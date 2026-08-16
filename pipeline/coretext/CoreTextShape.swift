// Shape Myanmar text with CoreText and print the glyph run.
//
// CI shapes with HarfBuzz. Apple platforms shape with CoreText, and the
// two can disagree — that is precisely what issue #14 asks people to
// check by hand. On a Mac this needs no hand at all: build once, and
// coretext_check.py diffs CoreText's glyph run against HarfBuzz's for
// every cluster in the corpus.
//
//   swiftc -O CoreTextShape.swift -o coretext-shape
//   ./coretext-shape <font.ttf> <text> [more text ...]
//
// Output, one line per input string, tab-separated:
//   <text>\t<glyphID>:<name>@<x>,<y> <glyphID>:<name>@<x>,<y> ...
// so a caller can compare names, order and positions.

import CoreText
import Foundation

func loadFont(_ path: String, size: CGFloat) -> CTFont? {
    guard let data = FileManager.default.contents(atPath: path) as CFData?,
          let provider = CGDataProvider(data: data),
          let cg = CGFont(provider) else { return nil }
    return CTFontCreateWithGraphicsFont(cg, size, nil, nil)
}

func shape(_ font: CTFont, _ text: String) -> String {
    // kCTFontAttributeName rather than AppKit's .font: this builds as a
    // plain Foundation + CoreText tool, no UI frameworks required
    let attrs = [kCTFontAttributeName: font] as CFDictionary
    let attributed = CFAttributedStringCreate(nil, text as CFString, attrs)!
    let line = CTLineCreateWithAttributedString(attributed)
    guard let runs = CTLineGetGlyphRuns(line) as? [CTRun] else { return "" }

    let ourName = CTFontCopyPostScriptName(font) as String

    var parts: [String] = []
    for run in runs {
        // CoreText silently falls back to another font for characters this
        // one lacks. Those glyph IDs belong to the FALLBACK font, so naming
        // them against ours invents glyphs that were never used — report
        // the substitution instead.
        let attrs = CTRunGetAttributes(run) as NSDictionary
        let runFont = attrs[kCTFontAttributeName as String] as! CTFont
        let runName = CTFontCopyPostScriptName(runFont) as String
        let isFallback = runName != ourName

        let count = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: count)
        var positions = [CGPoint](repeating: .zero, count: count)
        CTRunGetGlyphs(run, CFRangeMake(0, count), &glyphs)
        CTRunGetPositions(run, CFRangeMake(0, count), &positions)
        for i in 0..<count {
            let gid = glyphs[i]
            let p = positions[i]
            if isFallback {
                parts.append(String(format: "%d:<fallback:%@>@%.0f,%.0f",
                                    Int(gid), runName, p.x, p.y))
                continue
            }
            let name = (CTFontCopyNameForGlyph(font, gid) as String?) ?? "gid\(gid)"
            parts.append(String(format: "%d:%@@%.0f,%.0f",
                                Int(gid), name, p.x, p.y))
        }
    }
    return parts.joined(separator: " ")
}

let args = CommandLine.arguments
guard args.count >= 3, let font = loadFont(args[1], size: 1000) else {
    FileHandle.standardError.write(
        "usage: coretext-shape <font.ttf> <text> [text ...]\n".data(using: .utf8)!)
    exit(2)
}
for text in args.dropFirst(2) {
    print("\(text)\t\(shape(font, text))")
}
