"use client";

/**
 * Notes formatting toolbar — the visible editor chrome (PRODUCT_DESIGN_DECISIONS
 * §12). A single h-12 bar of icon buttons grouped by gap-4: Headings · Inline ·
 * Lists · Blocks · Link · [[wikilink]].
 *
 * Each control reads `editor.isActive(x)` for its active state (amber TEXT, not a
 * fill) and runs `editor.chain().focus().toggleX().run()`. Active reads are
 * recomputed only on the editor's `selectionUpdate`/`transaction`/`update`
 * events (subscribed below) so moving the cursor doesn't thrash React render.
 */

import { useCallback, useRef, useSyncExternalStore } from "react";
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
  Quote,
  SquareCode,
  Link as LinkIcon,
  Brackets,
} from "lucide-react";

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
        "flex size-8 items-center justify-center rounded-md transition-colors",
        "disabled:pointer-events-none disabled:opacity-40",
        active
          ? "text-amber-300"
          : "text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100",
      )}
    >
      <Icon size={16} strokeWidth={active ? 2.25 : 2} />
    </button>
  );
}

function Group({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-1">{children}</div>;
}

// ── NotesToolbar ────────────────────────────────────────────────────────────

export function NotesToolbar({ editor }: { editor: Editor | null }) {
  // Subscribe to editor changes so active states stay live without per-render thrash.
  useEditorTick(editor);

  if (!editor) {
    return <div className="border-charcoal-800 h-12 border-b" aria-hidden />;
  }

  const setLink = () => {
    const prev = (editor.getAttributes("link").href as string | undefined) ?? "";
    const href = window.prompt("Link URL", prev);
    if (href === null) return; // cancelled
    if (href.trim() === "") {
      editor.chain().focus().unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: href.trim() }).run();
  };

  const insertWikiLink = () => {
    // Inserting `[[` triggers the existing WikiLink suggestion (char: "[[").
    editor.chain().focus().insertContent("[[").run();
  };

  return (
    <div className="border-charcoal-800 flex h-12 items-center gap-4 border-b px-3">
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
      </Group>

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

      {/* Link + wikilink */}
      <Group>
        <ToolbarButton
          icon={LinkIcon}
          label="Link"
          active={editor.isActive("link")}
          onClick={setLink}
        />
        <ToolbarButton icon={Brackets} label="Insert [[wikilink]]" onClick={insertWikiLink} />
      </Group>
    </div>
  );
}
