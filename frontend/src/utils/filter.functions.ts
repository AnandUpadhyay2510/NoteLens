import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const InputSchema = z.object({
  syllabus: z.string().min(10).max(120_000),
  notes: z.string().min(10).max(200_000),
});

const GATEWAY = "https://ai.gateway.lovable.dev/v1/chat/completions";
const MODEL = "google/gemini-2.5-flash";

async function callLLM(messages: Array<{ role: string; content: string }>) {
  const key = process.env.LOVABLE_API_KEY;
  if (!key) throw new Error("LOVABLE_API_KEY missing");
  let lastErr: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(GATEWAY, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${key}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model: MODEL, messages }),
      });
      if (res.status === 429) throw new Error("Rate limited. Try again shortly.");
      if (res.status === 402)
        throw new Error("Lovable AI credits exhausted. Add credits in Settings → Workspace → Usage.");
      if (!res.ok) throw new Error(`LLM gateway error ${res.status}`);
      const data = await res.json();
      const text: string = data?.choices?.[0]?.message?.content ?? "";
      if (!text.trim()) throw new Error("Empty LLM response");
      return text;
    } catch (err) {
      lastErr = err;
      if (attempt < 2) await new Promise((r) => setTimeout(r, 500 * Math.pow(2, attempt)));
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("LLM call failed");
}

const STAGE1_SYSTEM = `You are an academic assistant. From the provided syllabus, extract:
- Core topics
- Subtopics
- Learning objectives

Return ONLY a structured bullet list. No prose. No explanations. No headings other than the topic names themselves. Use "- " for bullets and indent subtopics with two spaces.`;

const STAGE2_SYSTEM = `You are an academic notes filter. You will receive (1) a list of syllabus topics and (2) student notes.

For EACH section / paragraph / bullet of the notes:
- KEEP it verbatim if it is relevant to ANY syllabus topic (bias toward inclusion when borderline).
- REMOVE it if clearly unrelated.

Hard rules:
- Do NOT summarize.
- Do NOT rewrite or paraphrase kept content.
- Preserve original order, headings, bullets, and formatting of kept sections.
- If nothing is relevant, return exactly: (No relevant content found)

Return ONLY the filtered notes. No commentary.`;

export const runFilter = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => InputSchema.parse(input))
  .handler(async ({ data }) => {
    const topics = await callLLM([
      { role: "system", content: STAGE1_SYSTEM },
      { role: "user", content: `Syllabus:\n\n${data.syllabus}` },
    ]);

    const filtered = await callLLM([
      { role: "system", content: STAGE2_SYSTEM },
      {
        role: "user",
        content: `Syllabus topics:\n${topics}\n\n---\n\nStudent notes:\n${data.notes}`,
      },
    ]);

    return { topics: topics.trim(), filtered: filtered.trim() };
  });