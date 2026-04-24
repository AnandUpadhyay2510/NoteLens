import ReactMarkdown from "react-markdown";
import { Download } from "lucide-react";

type Props = {
  topics: string;
  filtered: string;
  loading: boolean;
  error: string | null;
};

export function OutputPanel({ topics, filtered, loading, error }: Props) {
  const empty = !loading && !error && !topics && !filtered;

  const handleDownload = () => {
    // Sanitize function to remove any accidental LLM chatter or echo
    const sanitize = (text: string) => {
      return text
        .replace(/^You are a precision academic parser\..*$/gm, "")
        .replace(/^You are an inclusive academic filter.*$/gm, "")
        .replace(/^===.*===$/gm, "")
        .trim();
    };

    const cleanTopics = sanitize(topics);
    const cleanFiltered = sanitize(filtered);

    const content = `# CodeLens Relevancy Report\n\n## Identified Syllabus Topics\n${cleanTopics}\n\n---\n\n## Filtered Study Notes\n${cleanFiltered}`;
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `codelens-report-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section
      className="relative rounded-md border border-border bg-card"
      style={{ boxShadow: "var(--shadow-paper)" }}
    >
      <header className="flex items-baseline justify-between border-b border-border px-6 py-4">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent">03</span>
          <h2 className="font-display text-3xl">Filtered Output</h2>
        </div>
        <div className="flex items-center gap-4">
          {(topics || filtered) && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground"
            >
              <Download size={14} />
              Download .md
            </button>
          )}
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            {loading ? "processing…" : filtered ? "complete" : "idle"}
          </span>
        </div>
      </header>

      <div className="grid gap-0 md:grid-cols-2 min-h-[500px]">
        <aside className="border-b border-border bg-secondary/20 p-8 md:border-b-0 md:border-r">
          <div className="sticky top-8">
            <p className="mb-6 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              Identified topics
            </p>
            {loading && !topics ? (
              <SkeletonLines n={6} />
            ) : topics ? (
              <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-foreground prose-p:text-foreground/80">
                <ReactMarkdown>{topics}</ReactMarkdown>
              </div>
            ) : (
              <p className="font-mono text-[12px] text-muted-foreground">—</p>
            )}
          </div>
        </aside>

        <article className="p-8">
          <p className="mb-6 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            Notes · syllabus-relevant only
          </p>
          {error ? (
            <div className="rounded border border-destructive/40 bg-destructive/5 p-4 font-mono text-[12px] text-destructive">
              {error}
            </div>
          ) : loading && !filtered ? (
            <SkeletonLines n={14} />
          ) : filtered ? (
            <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-foreground prose-p:text-foreground/80 prose-p:leading-relaxed">
              <ReactMarkdown>{filtered}</ReactMarkdown>
            </div>
          ) : empty ? (
            <p className="font-display text-xl italic text-muted-foreground">
              Your filtered notes will appear here.
            </p>
          ) : null}
        </article>
      </div>
    </section>
  );
}

function SkeletonLines({ n }: { n: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: n }).map((_, i) => (
        <div
          key={i}
          className="h-3 animate-pulse rounded bg-muted"
          style={{ width: `${60 + ((i * 13) % 40)}%` }}
        />
      ))}
    </div>
  );
}