"use client";

/**
 * Notes panel — Tiptap/Obsidian-grade markdown editor.
 *
 * Architecture:
 * - Tiptap v3 editor with StarterKit + Table(+row/cell/header) + Markdown +
 *   custom SlashCommandExtension + WikiLinkExtension.
 * - Markdown is the canonical store format: `editor.getMarkdown()` on debounced
 *   change → notesStore; `editor.commands.setContent(md)` on scope switch.
 * - Notes persist via two parallel paths:
 *   (a) workspace blob (existing sidecar autosave, always-written),
 *   (b) atomic `.md` file via Rust `write_text_atomic` (SC-032 crash-safe).
 * - Sharing: `.md`, PNG (html-to-image), and PDF (html-to-image → paginated
 *   jsPDF) all write real files via the Rust atomic-write commands through
 *   `@/lib/export-artifact` — the WKWebView blocks browser downloads.
 *
 * Static-export safe: `'use client'` + `immediatelyRender: false`.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { FileImage, FileText, Printer, Pencil } from "lucide-react";
import { EditorContent, useEditor } from "@tiptap/react";
import { StarterKit } from "@tiptap/starter-kit";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import { Markdown } from "@tiptap/markdown";

import { cn } from "@/lib/utils";
import { useNotesStore } from "@/store/notes";
import { useSymbolsStore } from "@/store/symbols";

import { saveTextArtifact, savePngArtifact, savePdfArtifact } from "@/lib/export-artifact";

import { SlashCommandExtension, type SlashMenuDetail } from "./SlashCommandExtension";
import { WikiLinkExtension, type WikiLinkItem, type WikiLinkMenuDetail } from "./WikiLinkExtension";
import { persistNoteMd } from "./notes-persistence";

// ── Debounce ──────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

// ── Scope chip label ──────────────────────────────────────────────────────────

function ScopeChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded px-2 py-0.5 text-xs font-medium transition-colors",
        active
          ? "bg-[var(--color-amber-500)] text-[var(--color-charcoal-950)]"
          : "bg-[var(--color-charcoal-800)] text-[var(--color-charcoal-300)] hover:bg-[var(--color-charcoal-700)]",
      )}
    >
      {label}
    </button>
  );
}

// ── NotesPanel ────────────────────────────────────────────────────────────────

export function NotesPanel() {
  const notesStore = useNotesStore();
  const symbolEntries = useSymbolsStore((s) => s.entries);

  // The current note scope: undefined = general, string = symbol.
  const scope = notesStore.focusSymbol;

  // --- Slash menu state ---
  const [slashMenu, setSlashMenu] = useState<SlashMenuDetail | null>(null);
  const [slashActiveIdx, setSlashActiveIdx] = useState(0);

  // --- WikiLink menu state ---
  const [wikiMenu, setWikiMenu] = useState<WikiLinkMenuDetail | null>(null);
  const [wikiActiveIdx, setWikiActiveIdx] = useState(0);

  // Ref to the editor container for PNG export.
  const editorContainerRef = useRef<HTMLDivElement>(null);

  // Build wikilink symbol list from watchlist + symbols-with-notes.
  const getWikiSymbols = useCallback((): WikiLinkItem[] => {
    const withNotes = new Set(notesStore.symbolsWithNotes());
    const allSymbols = symbolEntries.map((e) => e.symbol.toUpperCase());
    const merged = Array.from(new Set([...Array.from(withNotes), ...allSymbols]));
    return merged.map((sym) => ({ symbol: sym, hasNote: withNotes.has(sym) }));
  }, [notesStore, symbolEntries]);

  // Tiptap editor — `immediatelyRender: false` required for static export SSR-safety.
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Table.configure({ resizable: false }),
      TableRow,
      TableCell,
      TableHeader,
      Markdown,
      SlashCommandExtension,
      WikiLinkExtension.configure({ getSymbols: getWikiSymbols }),
    ],
    content: "",
    editorProps: {
      attributes: {
        class:
          "prose prose-invert prose-sm max-w-none min-h-[120px] p-3 outline-none focus:outline-none",
      },
    },
    onUpdate({ editor: e }) {
      // Handled below via subscription to avoid circular dep.
      void e;
    },
  });

  // --- Sync scope → editor ---
  const prevScopeRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (!editor) return;
    if (prevScopeRef.current === scope) return;
    prevScopeRef.current = scope;
    const md = notesStore.noteFor(scope);
    // setContent with contentType: 'markdown' — Markdown extension handles parsing.
    editor.commands.setContent(md || "", { contentType: "markdown" });
  }, [editor, scope, notesStore]);

  // --- Debounced save: editor → store → disk ---
  const [editorMarkdown, setEditorMarkdown] = useState("");

  useEffect(() => {
    if (!editor) return;
    const handler = () => {
      // `getMarkdown()` is added by the Markdown extension.
      const md = (editor as unknown as { getMarkdown: () => string }).getMarkdown();
      setEditorMarkdown(md);
    };
    editor.on("update", handler);
    return () => {
      editor.off("update", handler);
    };
  }, [editor]);

  const debouncedMd = useDebounce(editorMarkdown, 600);

  useEffect(() => {
    if (!debouncedMd && !editorMarkdown) return;
    // Write to the notes store. ("" = general scope, matching the store convention.)
    if (scope === "") {
      notesStore.setGeneral(debouncedMd);
    } else {
      notesStore.setSymbolNote(scope, debouncedMd);
    }
    // Fire-and-forget atomic .md write to disk.
    void persistNoteMd(scope, debouncedMd);
  }, [debouncedMd]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Listen for slash-menu events ---
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<SlashMenuDetail | null>).detail;
      setSlashMenu(detail);
      setSlashActiveIdx(0);
    };
    document.addEventListener("notes:slash-menu", handler);
    return () => document.removeEventListener("notes:slash-menu", handler);
  }, []);

  // --- Listen for wikilink-menu events ---
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<WikiLinkMenuDetail | null>).detail;
      setWikiMenu(detail);
      setWikiActiveIdx(0);
    };
    document.addEventListener("notes:wikilink-menu", handler);
    return () => document.removeEventListener("notes:wikilink-menu", handler);
  }, []);

  // --- Scope chips ---
  const symbolsWithNotes = notesStore.symbolsWithNotes();
  // Show general + up to 5 symbols with notes in the chips row.
  const chipSymbols = Array.from(new Set([...symbolsWithNotes, ...(scope ? [scope] : [])])).slice(
    0,
    8,
  );

  // --- Export handlers ---
  // Every export writes a real file via the Rust atomic-write commands (the
  // WKWebView blocks browser downloads). A transient status line confirms the
  // saved path so the user (and verification) can see it landed.
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const flashStatus = useCallback((msg: string) => {
    setExportStatus(msg);
    window.setTimeout(() => setExportStatus(null), 4500);
  }, []);

  const exportBaseName = scope ? scope.toUpperCase().replace(/[/\\]/g, "_") : "general";

  const handleExportMd = useCallback(async () => {
    const md = (editor as unknown as { getMarkdown: () => string } | null)?.getMarkdown() ?? "";
    try {
      const r = await saveTextArtifact("notes", `${exportBaseName}.md`, md);
      flashStatus(r.path ? `Saved ${r.path}` : "Downloaded .md");
    } catch (e) {
      flashStatus(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [editor, exportBaseName, flashStatus]);

  const handleExportPng = useCallback(async () => {
    const el = editorContainerRef.current;
    if (!el) return;
    try {
      const r = await savePngArtifact("notes", `${exportBaseName}.png`, el);
      flashStatus(r.path ? `Saved ${r.path}` : "Downloaded .png");
    } catch (e) {
      flashStatus(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [exportBaseName, flashStatus]);

  const handleExportPdf = useCallback(async () => {
    const el = editorContainerRef.current;
    if (!el) return;
    try {
      const r = await savePdfArtifact("notes", `${exportBaseName}.pdf`, el);
      flashStatus(r.path ? `Saved ${r.path}` : "Downloaded .pdf");
    } catch (e) {
      flashStatus(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [exportBaseName, flashStatus]);

  // --- Render ---
  return (
    <>
      <div className="notes-print-root flex h-full flex-col bg-[var(--color-charcoal-950)]">
        {/* Toolbar */}
        <div className="notes-toolbar flex items-center justify-between border-b border-[var(--color-charcoal-800)] px-3 py-2">
          <div className="flex items-center gap-1.5">
            <Pencil size={13} className="text-[var(--color-charcoal-400)]" />
            <span className="text-xs font-medium text-[var(--color-charcoal-300)]">Notes</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              title="Export .md"
              onClick={handleExportMd}
              className="rounded p-1 text-[var(--color-charcoal-400)] hover:bg-[var(--color-charcoal-800)] hover:text-[var(--color-charcoal-200)]"
            >
              <FileText size={13} />
            </button>
            <button
              type="button"
              title="Export PNG"
              onClick={handleExportPng}
              className="rounded p-1 text-[var(--color-charcoal-400)] hover:bg-[var(--color-charcoal-800)] hover:text-[var(--color-charcoal-200)]"
            >
              <FileImage size={13} />
            </button>
            <button
              type="button"
              title="Export PDF"
              onClick={handleExportPdf}
              className="rounded p-1 text-[var(--color-charcoal-400)] hover:bg-[var(--color-charcoal-800)] hover:text-[var(--color-charcoal-200)]"
            >
              <Printer size={13} />
            </button>
          </div>
        </div>

        {/* Export status — confirms the saved path so the user sees it landed. */}
        {exportStatus && (
          <div
            className="text-charcoal-400 border-charcoal-800 bg-charcoal-900 truncate border-b px-3 py-1.5 font-mono text-[11px]"
            title={exportStatus}
          >
            {exportStatus}
          </div>
        )}

        {/* Scope chips */}
        <div className="notes-scope-bar flex flex-wrap items-center gap-1.5 border-b border-[var(--color-charcoal-800)] px-3 py-1.5">
          <ScopeChip
            label="General"
            active={scope === ""}
            onClick={() => notesStore.setFocusSymbol("")}
          />
          {chipSymbols.map((sym) => (
            <ScopeChip
              key={sym}
              label={sym}
              active={scope === sym}
              onClick={() => notesStore.setFocusSymbol(sym)}
            />
          ))}
          {/* Add-symbol input for switching to an arbitrary symbol. */}
          <SymbolChipInput onCommit={(sym) => notesStore.setFocusSymbol(sym)} />
        </div>

        {/* Editor area */}
        <div ref={editorContainerRef} className="notes-editor-root flex-1 overflow-y-auto">
          <EditorContent editor={editor} />
        </div>
      </div>

      {/* Slash command popup */}
      {slashMenu && slashMenu.rect && slashMenu.items.length > 0 && (
        <div
          style={{
            position: "fixed",
            top: slashMenu.rect.bottom + 4,
            left: slashMenu.rect.left,
            zIndex: 9999,
            minWidth: 220,
            maxHeight: 320,
          }}
          className="overflow-y-auto rounded border border-[var(--color-charcoal-700)] bg-[var(--color-charcoal-900)] shadow-lg"
        >
          {slashMenu.items.map((item, i) => (
            <button
              key={item.title}
              type="button"
              className={cn(
                "flex w-full flex-col items-start px-3 py-2 text-left text-xs transition-colors",
                i === slashActiveIdx
                  ? "bg-[var(--color-charcoal-800)] text-[var(--color-charcoal-100)]"
                  : "text-[var(--color-charcoal-300)] hover:bg-[var(--color-charcoal-800)]",
              )}
              onMouseEnter={() => setSlashActiveIdx(i)}
              onClick={() => {
                slashMenu.command(item);
                setSlashMenu(null);
              }}
            >
              <span className="font-medium">{item.title}</span>
              <span className="text-[10px] text-[var(--color-charcoal-500)]">
                {item.description}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* WikiLink popup */}
      {wikiMenu && wikiMenu.rect && wikiMenu.items.length > 0 && (
        <div
          style={{
            position: "fixed",
            top: wikiMenu.rect.bottom + 4,
            left: wikiMenu.rect.left,
            zIndex: 9999,
            minWidth: 160,
            maxHeight: 240,
          }}
          className="overflow-y-auto rounded border border-[var(--color-charcoal-700)] bg-[var(--color-charcoal-900)] shadow-lg"
        >
          {wikiMenu.items.map((item, i) => (
            <button
              key={item.symbol}
              type="button"
              className={cn(
                "flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors",
                i === wikiActiveIdx
                  ? "bg-[var(--color-charcoal-800)] text-[var(--color-charcoal-100)]"
                  : "text-[var(--color-charcoal-300)] hover:bg-[var(--color-charcoal-800)]",
              )}
              onMouseEnter={() => setWikiActiveIdx(i)}
              onClick={() => {
                wikiMenu.command(item);
                setWikiMenu(null);
              }}
            >
              <span className="font-medium">{item.symbol}</span>
              {item.hasNote && (
                <span className="text-[10px] text-[var(--color-amber-400)]">has note</span>
              )}
            </button>
          ))}
        </div>
      )}
    </>
  );
}

// ── SymbolChipInput — type a symbol to switch scope ───────────────────────────

function SymbolChipInput({ onCommit }: { onCommit: (sym: string) => void }) {
  const [value, setValue] = useState("");
  const [editing, setEditing] = useState(false);

  const commit = () => {
    const sym = value.trim().toUpperCase();
    if (sym) onCommit(sym);
    setValue("");
    setEditing(false);
  };

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        className="rounded px-2 py-0.5 text-xs text-[var(--color-charcoal-500)] hover:text-[var(--color-charcoal-300)]"
      >
        + symbol
      </button>
    );
  }

  return (
    <input
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value.toUpperCase())}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") {
          setValue("");
          setEditing(false);
        }
      }}
      onBlur={commit}
      placeholder="AAPL"
      className="w-16 rounded border border-[var(--color-charcoal-700)] bg-[var(--color-charcoal-900)] px-2 py-0.5 text-xs text-[var(--color-charcoal-200)] outline-none placeholder:text-[var(--color-charcoal-600)]"
    />
  );
}
