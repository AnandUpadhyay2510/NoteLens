import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { Trash } from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [{ title: "CodeLens — History" }],
  }),
  component: HistoryPage,
});

function HistoryPage() {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadResults() {
    setLoading(true);
    try {
      const res = await fetchWithAuth("/filter/results");
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to load history");
      setResults(data.results);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      const res = await fetchWithAuth(`/filter/results/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      toast.success("Deleted");
      loadResults();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  useEffect(() => {
    loadResults();
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-5">
          <div className="flex items-baseline gap-3">
            <Link to="/" className="flex items-baseline gap-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-foreground font-mono text-[11px] font-medium text-background">
                C
              </div>
              <span className="font-display text-2xl">CodeLens</span>
            </Link>
          </div>
          <nav className="flex items-center gap-6 font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
            <Link to="/library" className="hover:text-foreground">Library</Link>
            <Link to="/" className="hover:text-foreground">Workspace</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-8 py-12">
        <h1 className="mb-8 font-display text-4xl">Filter History</h1>

        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-32 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : results.length === 0 ? (
          <p className="font-mono text-[13px] text-muted-foreground">
            No filter results yet. Run your first filter from the{" "}
            <Link to="/" className="text-accent underline">
              workspace
            </Link>
            .
          </p>
        ) : (
          <div className="space-y-6">
            {results.map((r: any) => (
              <details
                key={r.id}
                className="group rounded-md border border-border bg-card"
                style={{ boxShadow: "var(--shadow-paper)" }}
              >
                <summary className="flex cursor-pointer items-center justify-between px-6 py-4">
                  <div>
                    <p className="font-display text-xl">
                      {r.created_at
                        ? format(new Date(r.created_at), "MMM d, yyyy · h:mm a")
                        : "Unknown date"}
                    </p>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                      {r.processing_time_seconds}s · {r.model_used}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <button
                          onClick={(e) => e.stopPropagation()}
                          aria-label="Delete history item"
                          className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash size={16} />
                        </button>
                      </AlertDialogTrigger>
                      <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete this filtered result from your history.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDelete(r.id)}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          >
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </summary>
                <div className="border-t border-border grid gap-6 md:grid-cols-2 p-6">
                  <div>
                    <h3 className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground border-b border-border/50 pb-2">Identified Topics</h3>
                    <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-foreground">
                      <ReactMarkdown>{r.identified_topics || ""}</ReactMarkdown>
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-4 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground border-b border-border/50 pb-2">Filtered Notes</h3>
                    <div className="prose prose-sm max-w-none prose-headings:font-display prose-headings:text-foreground">
                      <ReactMarkdown>{r.filtered_notes || ""}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              </details>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
