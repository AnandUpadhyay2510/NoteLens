import { useRef, useState } from "react";
import { extractPdfText } from "@/lib/pdf";
import { toast } from "sonner";
import { fetchWithAuth } from "@/lib/api";

type Props = {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  accent?: boolean;
};

export function InputPanel({ label, hint, value, onChange, accent }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const isDoc = value.startsWith("DOC-");

  async function handleFile(f: File) {
    setBusy(true);
    try {
      // Try uploading to backend first
      const formData = new FormData();
      formData.append("file", f);

      const res = await fetchWithAuth("/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        onChange(`DOC-${data.id}`);
        setFileName(f.name);
        toast.success(`Uploaded ${f.name}`);
      } else {
        // Fallback: extract locally
        if (f.name.toLowerCase().endsWith(".pdf") || f.type === "application/pdf") {
          const text = await extractPdfText(f);
          onChange(text);
          setFileName(f.name);
          toast.success(`Extracted ${f.name}`);
        } else {
          const t = await f.text();
          onChange(t);
          setFileName(f.name);
          toast.success(`Loaded ${f.name}`);
        }
      }
    } catch (e) {
      // Fallback to local extraction on network error
      try {
        if (f.name.toLowerCase().endsWith(".pdf") || f.type === "application/pdf") {
          const text = await extractPdfText(f);
          onChange(text);
          setFileName(f.name);
          toast.success(`Extracted ${f.name} (local)`);
        } else {
          const t = await f.text();
          onChange(t);
          setFileName(f.name);
          toast.success(`Loaded ${f.name}`);
        }
      } catch {
        toast.error("Could not read file");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="group relative flex h-full flex-col rounded-md border border-border bg-card"
      style={{ boxShadow: "var(--shadow-paper)" }}
    >
      <div className="flex items-baseline justify-between border-b border-border px-5 py-3">
        <div className="flex items-baseline gap-3">
          <span
            className={`font-mono text-[10px] uppercase tracking-[0.2em] ${
              accent ? "text-accent" : "text-muted-foreground"
            }`}
          >
            {accent ? "02" : "01"}
          </span>
          <h2 className="font-display text-2xl">{label}</h2>
        </div>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground underline-offset-4 hover:text-foreground hover:underline disabled:opacity-50"
        >
          {busy ? "uploading…" : "upload file"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.txt,.md,.mp3,.wav,.m4a,.ogg,application/pdf,text/plain,audio/*"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
            e.target.value = "";
          }}
        />
      </div>

      {isDoc ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 py-8">
          <p className="font-mono text-[13px] text-foreground">
            📄 {fileName || "Remote Document"}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Uploaded to server · Ready for processing
          </p>
          <button
            onClick={() => {
              onChange("");
              setFileName(null);
            }}
            className="mt-2 font-mono text-[10px] uppercase tracking-widest text-accent underline underline-offset-4 hover:text-foreground"
          >
            clear
          </button>
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={hint}
          spellCheck={false}
          className="min-h-[260px] flex-1 resize-none bg-transparent px-5 py-4 font-mono text-[13px] leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus:outline-none"
        />
      )}

      <div className="flex items-center justify-between border-t border-dashed border-border px-5 py-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <span>{isDoc ? "document" : `${value.length.toLocaleString()} chars`}</span>
        <span>
          {isDoc
            ? fileName || "uploaded"
            : value
              ? `${value.split(/\s+/).filter(Boolean).length} words`
              : "—"}
        </span>
      </div>
    </div>
  );
}