"use client";

/**
 * Notes formatting toolbar — the visible editor chrome (PRODUCT_DESIGN_DECISIONS
 * §12). A wrapping bar of h-7 (28px) icon buttons with 14px icons — the Notes
 * surface's ONE icon ladder (R9 §3; the header pencil and exports match) — in
 * hairline-separated groups: Headings · Inline · Lists · Blocks · Link ·
 * [[wikilink]].
 *
 * Each control reads `editor.isActive(x)` for its active state (amber TEXT, not a
 * fill) and runs `editor.chain().focus().toggleX().run()`. Active reads are
 * recomputed only on the editor's `selectionUpdate`/`transaction`/`update`
 * events (subscribed below) so moving the cursor doesn't thrash React render.
 */

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { Editor } from "@tiptap/react";
import {
  Heading1,
  Heading2,
  Heading3,
  Bold,
  Italic,
  Code,
  List,
  ListOrdered,
  ListChecks,
  Quote,
  SquareCode,
  Link as LinkIcon,
  Brackets,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Active-state subscription ───────────────────────────────────────────────
// Recompute `isActive` reads only when the editor actually changes (selection,
// transaction, content) — not on every React render.

function subscribeEditor(editor: Editor, callback: () => void): () => void {
  editor.on("selectionUpdate", callback);
  editor.on("transaction", callback);
  editor.on("update", callback);
  return () => {
    editor.off("selectionUpdate", callback);
    editor.off("transaction", callback);
    editor.off("update", callback);
  };
}

/**
 * Stable hook: re-renders the toolbar only when the editor signals a change.
 * A monotonic ref counter (bumped inside the subscribe callback) is the
 * external store value — `getSnapshot` must return a CACHED, stable number
 * between events (reading `editor.state.tr.time` would allocate a fresh
 * `Date.now()` every render → React's "getSnapshot should be cached" loop).
 */
function useEditorTick(editor: Editor | null): number {
  const tickRef = useRef(0);

  const subscribe = useCallback(
    (cb: () => void) => {
      if (!editor) return () => {};
      return subscribeEditor(editor, () => {
        tickRef.current += 1;
        cb();
      });
    },
    [editor],
  );

  const getSnapshot = useCallback(() => tickRef.current, []);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

// ── ToolbarButton ───────────────────────────────────────────────────────────

function ToolbarButton({
  icon: Icon,
  label,
  active,
  disabled,
  onClick,
}: {
  icon: typeof Bold;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active ?? false}
      disabled={disabled}
      onMouseDown={(e) => e.preventDefault()} // keep editor selection on click
      onClick={onClick}
      className={cn(
        "rounded-control flex size-7 items-center justify-center transition-colors",
        "disabled:pointer-events-none disabled:opacity-40",
        active
          ? "text-charcoal-300"
          : "text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100",
      )}
    >
      {/* ONE icon ladder for the whole Notes surface (R9 §3): 14px inside the
          28px control — the header pencil and export icons match. */}
      <Icon
        className={cn("size-3.5" /* tokens-ok: 14px icon — R9 §3 rung for h-7 controls */)}
        strokeWidth={active ? 2.25 : 2}
      />
    </button>
  );
}

// ── Link popover ────────────────────────────────────────────────────────────
// R15-UI-025: `window.prompt` is a browser-only primitive WKWebView does not
// implement (it silently no-ops in the desktop app) — an inline popover
// replaces it, with the house click-outside/Escape idiom (ModelControl.tsx).

function LinkPopover({
  initialHref,
  hasLink,
  onApply,
  onRemove,
  onClose,
}: {
  initialHref: string;
  hasLink: boolean;
  onApply: (href: string) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  const [value, setValue] = useState(initialHref);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      const el = rootRef.current;
      if (el && event.target instanceof Node && !el.contains(event.target)) {
        onClose();
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return (
    <div
      ref={rootRef}
      role="dialog"
      aria-label="Edit link"
      className="border-charcoal-700 bg-charcoal-875 rounded-control absolute top-full left-0 z-30 mt-1 flex w-64 items-center gap-1 border p-1"
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        placeholder="https://…"
        aria-label="Link URL"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onApply(value.trim());
          }
        }}
        className="bg-charcoal-800 text-charcoal-100 text-caption rounded-control h-7 min-w-0 flex-1 px-2 outline-none"
      />
      {hasLink && (
        <Button type="button" size="xs" variant="ghost" onClick={onRemove}>
          Remove
        </Button>
      )}
      <Button type="button" size="xs" variant="outline" onClick={() => onApply(value.trim())}>
        Apply
      </Button>
    </div>
  );
}

function Group({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-1">{children}</div>;
}

/** Quiet hairline between toolbar groups — separation without loud gaps. */
function GroupRule() {
  return (
    <span aria-hidden className="h-4 w-px" style={{ backgroundColor: "var(--hairline-strong)" }} />
  );
}

// ── NotesToolbar ────────────────────────────────────────────────────────────

export function NotesToolbar({ editor }: { editor: Editor | null }) {
  // Subscribe to editor changes so active states stay live without per-render thrash.
  useEditorTick(editor);
  // R15-UI-025: hooks stay above the early return below (rules of hooks) even
  // though the popover only matters once `editor` is non-null.
  const [linkOpen, setLinkOpen] = useState(false);

  if (!editor) {
    // Placeholder matches the real bar's box (py-1 + h-7 row) — no layout jump.
    return (
      <div className="border-charcoal-800 flex items-center border-b px-3 py-1" aria-hidden>
        <span className="h-7" />
      </div>
    );
  }

  const applyLink = (href: string) => {
    if (href === "") {
      editor.chain().focus().unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange("link").setLink({ href }).run();
    }
    setLinkOpen(false);
  };

  const removeLink = () => {
    editor.chain().focus().unsetLink().run();
    setLinkOpen(false);
  };

  const insertWikiLink = () => {
    // R15-UI-024 repro e: this used to `insertContent("[[")` unconditionally,
    // which — like any insert into a non-empty selection — REPLACED the
    // selected text with the literal "[[" instead of linking it. Wrap a
    // selection directly as the link target; only fall back to the "[["
    // trigger (which opens the picker) when there is nothing selected.
    const { from, to, empty } = editor.state.selection;
    if (!empty) {
      const symbol = editor.state.doc.textBetween(from, to, " ").trim().toUpperCase();
      if (symbol) {
        editor
          .chain()
          .focus()
          .insertContentAt({ from, to }, { type: "wikiLinkNode", attrs: { symbol } })
          .run();
        return;
      }
    }
    editor.chain().focus().insertContent("[[").run();
  };

  return (
    // Content-sized (py, not fixed h) + wrap: at a narrow panel the groups
    // flow to a second row instead of clipping or overlapping (law §3.3/§3.4).
    <div className="border-charcoal-800 flex flex-wrap items-center gap-2 border-b px-3 py-1">
      {/* Headings */}
      <Group>
        <ToolbarButton
          icon={Heading1}
          label="Heading 1"
          active={editor.isActive("heading", { level: 1 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        />
        <ToolbarButton
          icon={Heading2}
          label="Heading 2"
          active={editor.isActive("heading", { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        />
        <ToolbarButton
          icon={Heading3}
          label="Heading 3"
          active={editor.isActive("heading", { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        />
      </Group>
      <GroupRule />

      {/* Inline */}
      <Group>
        <ToolbarButton
          icon={Bold}
          label="Bold"
          active={editor.isActive("bold")}
          onClick={() => editor.chain().focus().toggleBold().run()}
        />
        <ToolbarButton
          icon={Italic}
          label="Italic"
          active={editor.isActive("italic")}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        />
        <ToolbarButton
          icon={Code}
          label="Inline code"
          active={editor.isActive("code")}
          onClick={() => editor.chain().focus().toggleCode().run()}
        />
      </Group>
      <GroupRule />

      {/* Lists */}
      <Group>
        <ToolbarButton
          icon={List}
          label="Bullet list"
          active={editor.isActive("bulletList")}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        />
        <ToolbarButton
          icon={ListOrdered}
          label="Numbered list"
          active={editor.isActive("orderedList")}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        />
        <ToolbarButton
          icon={ListChecks}
          label="Task list"
          active={editor.isActive("taskList")}
          onClick={() => editor.chain().focus().toggleTaskList().run()}
        />
      </Group>
      <GroupRule />

      {/* Blocks */}
      <Group>
        <ToolbarButton
          icon={Quote}
          label="Blockquote"
          active={editor.isActive("blockquote")}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
        />
        <ToolbarButton
          icon={SquareCode}
          label="Code block"
          active={editor.isActive("codeBlock")}
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        />
      </Group>
      <GroupRule />

      {/* Link + wikilink */}
      <Group>
        <div className="relative">
          <ToolbarButton
            icon={LinkIcon}
            label="Link"
            active={editor.isActive("link")}
            onClick={() => setLinkOpen((v) => !v)}
          />
          {linkOpen && (
            <LinkPopover
              initialHref={(editor.getAttributes("link").href as string | undefined) ?? ""}
              hasLink={editor.isActive("link")}
              onApply={applyLink}
              onRemove={removeLink}
              onClose={() => setLinkOpen(false)}
            />
          )}
        </div>
        <ToolbarButton icon={Brackets} label="Insert [[wikilink]]" onClick={insertWikiLink} />
      </Group>
    </div>
  );
}
