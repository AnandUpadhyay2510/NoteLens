import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { InputPanel } from "@/components/notelens/InputPanel";
import { OutputPanel } from "@/components/notelens/OutputPanel";
import { fetchWithAuth, getToken } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CodeLens — Syllabus-aware notes filter" },
      {
        name: "description",
        content:
          "Reduce student notes to only syllabus-relevant content. Deterministic two-stage LLM pipeline.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  const [syllabus, setSyllabus] = useState("");
  const [notes, setNotes] = useState("");
  const [topics, setTopics] = useState("");
  const [filtered, setFiltered] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  async function onRun() {
    if (syllabus.trim().length < 10 || notes.trim().length < 10) {
      toast.error("Both syllabus and notes need at least 10 characters.");
      return;
    }

    if (!getToken()) {
      toast.error("Please log in first.");
      return;
    }

    setLoading(true);
    setError(null);
    setTopics("");
    setFiltered("");
    setProgress(0);

    try {
      const payload: any = {};

      // Determine if text or doc_id
      if (syllabus.startsWith("DOC-")) {
        payload.syllabus_doc_id = syllabus.replace("DOC-", "");
      } else {
        payload.syllabus_text = syllabus;
      }

      if (notes.startsWith("DOC-")) {
        payload.notes_doc_id = notes.replace("DOC-", "");
      } else {
        payload.notes_text = notes;
      }

      setProgress(20);

      const res = await fetchWithAuth("/filter/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      setProgress(80);

      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        throw new Error("Server returned an invalid response. Please try again.");
      }

      if (!res.ok) throw new Error(data.detail || data.message || "Pipeline failed");

      setTopics(data.result.identified_topics || "");
      setFiltered(data.result.filtered_notes || "");
      setProgress(100);
      toast.success(`Notes filtered in ${data.processing_time_seconds}s`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Pipeline failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  function onReset() {
    setSyllabus("");
    setNotes("");
    setTopics("");
    setFiltered("");
    setError(null);
    setProgress(0);
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-5">
          <div className="flex items-baseline gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-foreground font-mono text-[11px] font-medium text-background">
              C
            </div>
            <span className="font-display text-2xl">CodeLens</span>
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
              v1 · web
            </span>
          </div>
          <nav className="flex items-center gap-6 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
            <Link to="/library" className="hover:text-foreground">
              library
            </Link>
            <Link to="/history" className="hover:text-foreground">
              history
            </Link>
            <Link to="/login" className="hover:text-foreground">
              account
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-[1400px] gap-10 px-8 py-16 md:grid-cols-[1.4fr_1fr] md:py-24">
          <div>
            <p className="mb-6 font-mono text-[11px] uppercase tracking-[0.3em] text-accent">
              ── A deterministic pipeline, not AI magic
            </p>
            <h1 className="font-display text-5xl leading-[0.95] md:text-7xl">
              Reduce your notes to <em className="text-accent">only</em> what the syllabus
              actually asks for.
            </h1>
            <p className="mt-6 max-w-xl font-mono text-[13px] leading-relaxed text-muted-foreground">
              Drop in a syllabus and a pile of notes. Two scoped LLM passes: extract topics,
              then keep or remove each section. Structure preserved. No rewrites. No
              hallucinated content.
            </p>
          </div>
          <aside className="self-end border-l border-border pl-6 font-mono text-[11px] leading-relaxed text-muted-foreground">
            <p className="mb-3 uppercase tracking-[0.2em] text-foreground">Pipeline</p>
            <ol className="space-y-1.5">
              <li>extract → syllabus topics</li>
              <li>filter → keep / remove sections</li>
              <li>preserve → order &amp; structure</li>
            </ol>
          </aside>
        </div>
      </section>

      {/* Workspace */}
      <main className="mx-auto max-w-[1400px] px-8 py-12">
        <div className="grid gap-6 md:grid-cols-2">
          <InputPanel
            label="Syllabus"
            hint="Paste syllabus text, or upload a PDF/TXT file."
            value={syllabus}
            onChange={setSyllabus}
          />
          <InputPanel
            label="Notes"
            hint="Paste your notes, or upload a PDF/TXT/Audio recording."
            value={notes}
            onChange={setNotes}
            accent
          />
        </div>

        {/* Action Area */}
        <div className="mt-6 flex flex-col items-center gap-6">
          <div className="flex w-full flex-wrap items-center justify-between gap-4 border-y border-dashed border-border py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              Stage 1 → topics · Stage 2 → filter · Sequential calls
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={onReset}
                disabled={loading}
                className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:opacity-40"
              >
                reset
              </button>
              <button
                onClick={onRun}
                disabled={loading}
                className="group inline-flex items-center gap-3 rounded-sm bg-foreground px-6 py-3 font-mono text-[11px] uppercase tracking-[0.25em] text-background transition-all hover:bg-accent disabled:opacity-50"
              >
                <span>{loading ? "filtering…" : "run filter"}</span>
                <span className="transition-transform group-hover:translate-x-0.5">→</span>
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          {loading && (
            <div className="w-full max-w-md">
              <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-2 text-center font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {progress < 50 ? "Stage 1 · extracting topics…" : "Stage 2 · filtering notes…"}
              </p>
            </div>
          )}
        </div>

        <div className="mt-6">
          <OutputPanel topics={topics} filtered={filtered} loading={loading} error={error} />
        </div>

        {/* How it works */}
        <section id="how" className="mt-24 border-t border-border pt-16">
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-accent">
            ── Design principles
          </p>
          <h2 className="mt-3 font-display text-4xl md:text-5xl">
            Pipeline over abstraction.
          </h2>
          <div className="mt-10 grid gap-10 md:grid-cols-3">
            {PRINCIPLES.map((p, i) => (
              <div key={p.title} className="border-t border-border pt-5">
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="mt-2 font-display text-2xl">{p.title}</h3>
                <p className="mt-2 font-mono text-[12px] leading-relaxed text-muted-foreground">
                  {p.body}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="mt-16 border-t border-border">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-8 py-6 font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          <span>CodeLens · open source · v1</span>
          <span>fail fast · preserve structure · llm as a function</span>
        </div>
      </footer>
    </div>
  );
}

const PRINCIPLES = [
  {
    title: "Fail early, fail loudly",
    body: "Empty PDFs and unsupported formats stop the run with an actionable error. No silent partial output.",
  },
  {
    title: "LLM as a function",
    body: "Two tightly-scoped prompts. Stage 1 returns a list. Stage 2 keeps or removes. No open-ended generation.",
  },
  {
    title: "Preserve > rewrite",
    body: "Filtered notes keep your original wording, headings, and order. We remove. We never paraphrase.",
  },
];
