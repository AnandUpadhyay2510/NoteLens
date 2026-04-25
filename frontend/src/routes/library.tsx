import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { toast } from "sonner";
import { format } from "date-fns";
import { Trash, FileText, Mic } from "lucide-react";

export const Route = createFileRoute("/library")({
  head: () => ({
    meta: [{ title: "CodeLens — Document Library" }],
  }),
  component: LibraryPage,
});

function LibraryPage() {
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadDocs() {
    setLoading(true);
    try {
      const res = await fetchWithAuth("/documents");
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to load documents");
      setDocs(data.documents);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      const res = await fetchWithAuth(`/documents/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      toast.success("Document deleted");
      loadDocs();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  useEffect(() => {
    loadDocs();
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
            <Link to="/" className="hover:text-foreground">Workspace</Link>
            <Link to="/history" className="hover:text-foreground">History</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-8 py-12">
        <h1 className="mb-8 font-display text-4xl">Document Library</h1>

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-32 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : docs.length === 0 ? (
          <p className="font-mono text-[13px] text-muted-foreground">
            No documents uploaded yet. Upload files from the{" "}
            <Link to="/" className="text-accent underline">
              workspace
            </Link>
            .
          </p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {docs.map((doc: any) => (
              <div
                key={doc.id}
                className="group rounded-md border border-border bg-card p-5 transition-shadow hover:shadow-md"
                style={{ boxShadow: "var(--shadow-paper)" }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {doc.file_type === "audio" ? (
                      <Mic size={20} className="text-accent" />
                    ) : (
                      <FileText size={20} className="text-accent" />
                    )}
                    <div>
                      <p className="font-display text-lg leading-tight">
                        {doc.filename || "Untitled"}
                      </p>
                      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                        {doc.file_type || "text"} ·{" "}
                        {doc.created_at
                          ? format(new Date(doc.created_at), "MMM d, yyyy")
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="rounded p-1 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash size={14} />
                  </button>
                </div>
                <p className="mt-3 font-mono text-[11px] text-muted-foreground">
                  {doc.extracted_text
                    ? `${doc.extracted_text.length.toLocaleString()} chars extracted`
                    : "Processing…"}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
