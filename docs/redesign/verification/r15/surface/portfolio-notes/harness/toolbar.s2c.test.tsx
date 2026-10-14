import { test } from "vitest";
import fs from "fs";
import { render, cleanup, act, screen, fireEvent } from "@testing-library/react";
window.history.replaceState({}, "", `/?sidecar-port=52221`);
(document as any).elementFromPoint ??= () => null;
(Range.prototype as any).getClientRects ??= () => ({ length: 0, item: () => null, [Symbol.iterator]: function* () {} });
(Range.prototype as any).getBoundingClientRect ??= () => ({ x: 0, y: 0, top: 0, left: 0, bottom: 0, right: 0, width: 0, height: 0 });
(Element.prototype as any).getClientRects ??= () => [];
import { useNotesStore } from "@/store/notes";
import { NotesPanel } from "@/modules/notes/NotesPanel";
const OUT = "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2c/out/notes-toolbar-replay.json";
const wait = (ms: number) => act(async () => { await new Promise((r) => setTimeout(r, ms)); });
test("T1 toolbar buttons on a selection", async () => {
  useNotesStore.setState({ general: "alpha beta gamma", bySymbol: {}, focusSymbol: "" } as any);
  const { container } = render(<NotesPanel />);
  await wait(300);
  const ed = (container.querySelector(".ProseMirror") as any).editor;
  const out: Record<string, unknown> = {};
  for (const label of ["Heading 1", "Heading 2", "Heading 3", "Bold", "Italic", "Inline code", "Bullet list", "Numbered list", "Blockquote", "Code block", "Insert [[wikilink]]"]) {
    await act(async () => { ed.commands.setContent("alpha beta gamma"); ed.commands.setTextSelection({ from: 1, to: 6 }); });
    const btn = screen.getByLabelText(label);
    await act(async () => { fireEvent.click(btn); });
    await wait(30);
    out[label] = { html: container.querySelector(".ProseMirror")!.innerHTML.slice(0, 140), pressed: btn.getAttribute("aria-pressed") };
  }
  (window as any).prompt = () => "https://example.org";
  await act(async () => { ed.commands.setContent("alpha beta gamma"); ed.commands.setTextSelection({ from: 1, to: 6 }); });
  await act(async () => { fireEvent.click(screen.getByLabelText("Link")); });
  out["Link(prompt stubbed)"] = container.querySelector(".ProseMirror")!.innerHTML.slice(0, 200);
  (window as any).prompt = undefined;
  let err: string | null = null;
  try { await act(async () => { fireEvent.click(screen.getByLabelText("Link")); }); } catch (e) { err = String(e); }
  out["Link(no prompt, as Tauri WKWebView)"] = { error: err };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  cleanup();
});
