/**
 * Shared export helpers — write Markdown / PNG / PDF artifacts to disk.
 *
 * The WKWebView/Chromium webview blocks the browser `<a download>` + Blob-save
 * path, so every binary export flows through the Rust `write_bytes_atomic`
 * command (text goes through `write_text_atomic`). Both write atomically
 * (temp-file + rename) under `{dataDir}/exports/<subdir>/`, where `dataDir` is
 * the sidecar's `--data-dir` reported by `GET /health`.
 *
 * Outside Tauri (browser dev) the helpers fall back to a Blob download so the
 * affordance is never silently dead, and return `{ path: null, fellBack: true }`.
 *
 * `html-to-image` and `jspdf` are imported lazily so they never enter the
 * initial bundle or run during SSR/static-export.
 */

import { invoke } from "@tauri-apps/api/core";

export interface ExportResult {
  /** Absolute path written on disk (Tauri), or null when a browser fallback ran. */
  path: string | null;
  /** True when the browser Blob-download fallback was used (non-Tauri dev). */
  fellBack: boolean;
}

function inTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

let dataDirCache: string | null = null;

/** Resolve the sidecar data dir (cached) from `GET /health` → `data_dir`. */
async function resolveDataDir(): Promise<string | null> {
  if (dataDirCache !== null) return dataDirCache;
  if (!inTauri()) return null;
  try {
    const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");
    const base = await getSidecarBaseUrl();
    const response = await fetch(`${base}/health`);
    if (!response.ok) return null;
    const health = (await response.json()) as { data_dir?: string };
    if (health.data_dir) {
      dataDirCache = health.data_dir;
      return health.data_dir;
    }
  } catch {
    // Non-fatal.
  }
  return null;
}

/** Trigger a browser Blob download (dev fallback only). */
function browserDownload(filename: string, blob: Blob): void {
  if (typeof document === "undefined") return;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** Write UTF-8 text (e.g. Markdown) to `{dataDir}/exports/<subdir>/<filename>`. */
export async function saveTextArtifact(
  subdir: string,
  filename: string,
  text: string,
): Promise<ExportResult> {
  const dir = await resolveDataDir();
  if (dir) {
    const path = `${dir}/exports/${subdir}/${filename}`;
    await invoke("write_text_atomic", { path, contents: text });
    return { path, fellBack: false };
  }
  browserDownload(filename, new Blob([text], { type: "text/markdown" }));
  return { path: null, fellBack: true };
}

/** Write raw bytes to `{dataDir}/exports/<subdir>/<filename>` via the Rust command. */
async function saveBytesArtifact(
  subdir: string,
  filename: string,
  bytes: Uint8Array,
  mime: string,
): Promise<ExportResult> {
  const dir = await resolveDataDir();
  if (dir) {
    const path = `${dir}/exports/${subdir}/${filename}`;
    // serde decodes a JSON number array straight into Rust `Vec<u8>`.
    await invoke("write_bytes_atomic", { path, contents: Array.from(bytes) });
    return { path, fellBack: false };
  }
  // `bytes` always wraps a full fresh buffer here; pass it as ArrayBuffer so the
  // Blob ctor type-checks under TS 5.7's generic Uint8Array<ArrayBufferLike>.
  browserDownload(filename, new Blob([bytes.buffer as ArrayBuffer], { type: mime }));
  return { path: null, fellBack: true };
}

/** Rasterize a DOM element to a PNG data URL on the warm-graphite panel bg. */
async function elementToPngDataUrl(el: HTMLElement, pixelRatio = 2): Promise<string> {
  const { toPng } = await import("html-to-image");
  return toPng(el, {
    pixelRatio,
    backgroundColor: "#1a1814", // charcoal-900 — never transparent/black
    cacheBust: true,
  });
}

async function dataUrlToBytes(dataUrl: string): Promise<Uint8Array> {
  const res = await fetch(dataUrl);
  return new Uint8Array(await res.arrayBuffer());
}

/** Export a DOM element as a PNG file. */
export async function savePngArtifact(
  subdir: string,
  filename: string,
  el: HTMLElement,
  pixelRatio = 2,
): Promise<ExportResult> {
  const dataUrl = await elementToPngDataUrl(el, pixelRatio);
  const bytes = await dataUrlToBytes(dataUrl);
  return saveBytesArtifact(subdir, filename, bytes, "image/png");
}

/**
 * Export a DOM element as a paginated A4 PDF (image-based: the element is
 * rasterized to PNG, scaled to page width, and sliced across pages). This
 * always produces a valid, openable PDF that mirrors the rendered surface.
 */
export async function savePdfArtifact(
  subdir: string,
  filename: string,
  el: HTMLElement,
  pixelRatio = 2,
): Promise<ExportResult> {
  const dataUrl = await elementToPngDataUrl(el, pixelRatio);

  // Measure the rasterized image.
  const img = new Image();
  img.src = dataUrl;
  await img.decode();
  const imgW = img.naturalWidth;
  const imgH = img.naturalHeight;

  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const scaledH = (imgH * pageW) / imgW; // fit to page width, keep aspect

  // First page, then slice downward by negative y-offset per the canonical
  // jsPDF pagination pattern.
  let heightLeft = scaledH;
  pdf.addImage(dataUrl, "PNG", 0, 0, pageW, scaledH);
  heightLeft -= pageH;
  while (heightLeft > 0) {
    const position = heightLeft - scaledH; // negative offset
    pdf.addPage();
    pdf.addImage(dataUrl, "PNG", 0, position, pageW, scaledH);
    heightLeft -= pageH;
  }

  const bytes = new Uint8Array(pdf.output("arraybuffer"));
  return saveBytesArtifact(subdir, filename, bytes, "application/pdf");
}
