// src-tauri/dmg/generate-background.swift
//
// Generates the dmg first-open background (660x400, matching src-tauri/tauri.conf.json's
// bundle.macOS.dmg). Icon anchors live at y=150 (app at x=180, Applications link at
// x=480, same as tauri.conf.json's appPosition/applicationFolderPosition) so this image
// only needs to leave room above the text for Finder's own icon + label rendering, draw a
// connecting arrow between them, and spell out the Gatekeeper "Open Anyway" step below.
//
// Run: swift src-tauri/dmg/generate-background.swift [output-path]  (default: ./background.png)
//
// AppKit/CoreGraphics only — no new dependency for a one-off asset (ponytail rung 4).
import AppKit

let width = 660
let height = 400
let outputPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "background.png"

// Matches the app's zinc/cool-indigo palette (styles/tokens.css design tokens).
let zincBg = NSColor(srgbRed: 0.055, green: 0.055, blue: 0.067, alpha: 1) // zinc-950-ish
let zincBg2 = NSColor(srgbRed: 0.102, green: 0.102, blue: 0.118, alpha: 1) // zinc-900-ish
let indigo = NSColor(srgbRed: 0.388, green: 0.400, blue: 0.945, alpha: 1) // cool-indigo accent
let textPrimary = NSColor(srgbRed: 0.953, green: 0.953, blue: 0.961, alpha: 1)
let textSecondary = NSColor(srgbRed: 0.627, green: 0.627, blue: 0.667, alpha: 1)

guard
  let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: width,
    pixelsHigh: height,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
  )
else {
  fatalError("could not allocate bitmap")
}
rep.size = NSSize(width: width, height: height)

guard let ctx = NSGraphicsContext(bitmapImageRep: rep) else {
  fatalError("could not create graphics context")
}
NSGraphicsContext.current = ctx

// `ty` converts a "distance from the top" (how icon positions in tauri.conf.json's dmg
// config are expressed) into the bottom-up y this un-flipped context draws with.
func ty(_ fromTop: CGFloat, height boxHeight: CGFloat = 0) -> CGFloat {
  CGFloat(height) - fromTop - boxHeight
}

let fullRect = NSRect(x: 0, y: 0, width: width, height: height)
NSGradient(starting: zincBg, ending: zincBg2)!.draw(in: fullRect, angle: 90)

// Arrow between the two icon anchors (both at y=150-from-top, x=180/480 — tauri.conf.json's
// appPosition / applicationFolderPosition), drawn behind where Finder renders the live icons.
let arrowY = ty(150)
let arrow = NSBezierPath()
let arrowStartX: CGFloat = 255
let arrowEndX: CGFloat = 400
arrow.move(to: NSPoint(x: arrowStartX, y: arrowY))
arrow.line(to: NSPoint(x: arrowEndX, y: arrowY))
arrow.move(to: NSPoint(x: arrowEndX - 10, y: arrowY + 7))
arrow.line(to: NSPoint(x: arrowEndX, y: arrowY))
arrow.line(to: NSPoint(x: arrowEndX - 10, y: arrowY - 7))
arrow.lineWidth = 2.5
indigo.withAlphaComponent(0.85).setStroke()
arrow.stroke()

func centeredText(_ text: String, font: NSFont, color: NSColor, topY: CGFloat, boxHeight: CGFloat) {
  let paragraph = NSMutableParagraphStyle()
  paragraph.alignment = .center
  paragraph.lineSpacing = 3
  let attrs: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: color,
    .paragraphStyle: paragraph,
  ]
  let rect = NSRect(x: 40, y: ty(topY, height: boxHeight), width: CGFloat(width) - 80, height: boxHeight)
  NSAttributedString(string: text, attributes: attrs).draw(in: rect)
}

centeredText(
  "Drag Vysted Terminal to Applications",
  font: NSFont.boldSystemFont(ofSize: 16),
  color: textPrimary,
  topY: 258,
  boxHeight: 22
)

centeredText(
  "First open: macOS says it can't check the app for malware.\n"
    + "Open System Settings \u{2192} Privacy & Security, scroll down,\n"
    + "and click Open Anyway (once).",
  font: NSFont.systemFont(ofSize: 12.5),
  color: textSecondary,
  topY: 288,
  boxHeight: 70
)

NSGraphicsContext.current = nil

guard let png = rep.representation(using: .png, properties: [:]) else {
  fatalError("could not encode PNG")
}
do {
  try png.write(to: URL(fileURLWithPath: outputPath))
} catch {
  fatalError("could not write \(outputPath): \(error)")
}

// Self-check: a 660x400 image was actually written.
let written = NSImage(contentsOfFile: outputPath)
precondition(written != nil, "wrote \(outputPath) but it does not decode as an image")
precondition(
  written!.representations.first!.pixelsWide == width
    && written!.representations.first!.pixelsHigh == height,
  "unexpected output size"
)
print("[dmg] wrote \(outputPath) (\(width)x\(height))")
