// Shape Myanmar text with DirectWrite and print the glyph run.
//
// CI shapes with HarfBuzz. Windows shapes with DirectWrite, and the two
// can disagree — that is the half of issue #14 that automation was
// supposed to be unable to reach. It can: GitHub's windows-latest runner
// is a real Windows box with the real engine, so this needs no volunteer
// and no Visual Studio project, just the compiler already on the runner.
//
//   cl /EHsc /O2 /std:c++17 DirectWriteShape.cpp
//   DirectWriteShape.exe <font.ttf> <corpus-utf8.txt> [emSize] [locale]
//
// This calls IDWriteTextAnalyzer directly — GetGlyphs then
// GetGlyphPlacements — which is DirectWrite's actual OpenType shaping
// engine, the same code path IDWriteTextLayout runs internally. Going
// through the analyzer rather than a layout keeps the font under test the
// ONLY font in play: at this layer DirectWrite never silently falls back
// to another family, so a character the font lacks comes back as glyph 0
// and compares straight against HarfBuzz's .notdef.
//
// Input is a UTF-8 file, one string per line, rather than argv: the corpus
// is thousands of clusters (past any command-line length limit) and a file
// sidesteps the console code page entirely.
//
// Output is deliberately pure ASCII, one line per input line, in order:
//
//   <line-index>\t<glyphID>@<x>,<y> <glyphID>@<x>,<y> ...
//
// Glyph IDs, not names — DirectWrite does not expose `post` names, and the
// caller maps IDs through the same fontTools glyph order it uses for
// HarfBuzz, so both engines end up naming glyphs identically. Positions
// are pen-relative and in the em size passed in (the caller passes 1000,
// matching the units HarfBuzz is scaled to).

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <dwrite.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cwchar>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#pragma comment(lib, "dwrite.lib")

namespace {

// One script-analysis run: the itemiser tells us which stretch of the
// string is Myanmar (and which OpenType script to shape it with).
struct ScriptRun {
    UINT32 start;
    UINT32 length;
    DWRITE_SCRIPT_ANALYSIS analysis;
};

// The analyzer reads the text through this. Both COM objects below live on
// the stack for one call, so reference counting is a formality — hence the
// fixed refcounts.
class TextSource : public IDWriteTextAnalysisSource {
public:
    TextSource(const wchar_t* text, UINT32 length, const wchar_t* locale)
        : text_(text), length_(length), locale_(locale) {}

    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** object) override {
        if (iid == __uuidof(IUnknown) ||
            iid == __uuidof(IDWriteTextAnalysisSource)) {
            *object = static_cast<IDWriteTextAnalysisSource*>(this);
            return S_OK;
        }
        *object = nullptr;
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return 1; }
    ULONG STDMETHODCALLTYPE Release() override { return 1; }

    HRESULT STDMETHODCALLTYPE GetTextAtPosition(
            UINT32 position, WCHAR const** text, UINT32* length) override {
        if (position >= length_) {
            *text = nullptr;
            *length = 0;
        } else {
            *text = text_ + position;
            *length = length_ - position;
        }
        return S_OK;
    }

    HRESULT STDMETHODCALLTYPE GetTextBeforePosition(
            UINT32 position, WCHAR const** text, UINT32* length) override {
        if (position == 0 || position > length_) {
            *text = nullptr;
            *length = 0;
        } else {
            *text = text_;
            *length = position;
        }
        return S_OK;
    }

    DWRITE_READING_DIRECTION STDMETHODCALLTYPE
    GetParagraphReadingDirection() override {
        return DWRITE_READING_DIRECTION_LEFT_TO_RIGHT;
    }

    HRESULT STDMETHODCALLTYPE GetLocaleName(
            UINT32 position, UINT32* length, WCHAR const** name) override {
        *length = (position < length_) ? length_ - position : 0;
        *name = locale_;
        return S_OK;
    }

    HRESULT STDMETHODCALLTYPE GetNumberSubstitution(
            UINT32 position, UINT32* length,
            IDWriteNumberSubstitution** substitution) override {
        *length = (position < length_) ? length_ - position : 0;
        *substitution = nullptr;   // never substitute: ၀-၉ must stay as typed
        return S_OK;
    }

private:
    const wchar_t* text_;
    UINT32 length_;
    const wchar_t* locale_;
};

// ...and writes its itemisation back through this. Only the script runs
// matter here; line breaking and bidi are someone else's problem.
class TextSink : public IDWriteTextAnalysisSink {
public:
    std::vector<ScriptRun> runs;

    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** object) override {
        if (iid == __uuidof(IUnknown) ||
            iid == __uuidof(IDWriteTextAnalysisSink)) {
            *object = static_cast<IDWriteTextAnalysisSink*>(this);
            return S_OK;
        }
        *object = nullptr;
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return 1; }
    ULONG STDMETHODCALLTYPE Release() override { return 1; }

    HRESULT STDMETHODCALLTYPE SetScriptAnalysis(
            UINT32 position, UINT32 length,
            DWRITE_SCRIPT_ANALYSIS const* analysis) override {
        runs.push_back(ScriptRun{position, length, *analysis});
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE SetLineBreakpoints(
            UINT32, UINT32, DWRITE_LINE_BREAKPOINT const*) override {
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE SetBidiLevel(
            UINT32, UINT32, UINT8, UINT8) override {
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE SetNumberSubstitution(
            UINT32, UINT32, IDWriteNumberSubstitution*) override {
        return S_OK;
    }
};

std::wstring widen(const std::string& utf8) {
    if (utf8.empty()) return std::wstring();
    int needed = MultiByteToWideChar(CP_UTF8, 0, utf8.data(),
                                     static_cast<int>(utf8.size()),
                                     nullptr, 0);
    if (needed <= 0) return std::wstring();
    std::wstring wide(static_cast<size_t>(needed), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.data(),
                        static_cast<int>(utf8.size()), &wide[0], needed);
    return wide;
}

// Shape one string. Returns the glyph run as ASCII, or a "!reason" token
// the caller turns into a hard error.
std::string shapeLine(IDWriteTextAnalyzer* analyzer, IDWriteFontFace* face,
                      const std::wstring& text, float emSize,
                      const wchar_t* locale) {
    if (text.empty()) return std::string();
    const UINT32 length = static_cast<UINT32>(text.size());

    TextSource source(text.c_str(), length, locale);
    TextSink sink;
    if (FAILED(analyzer->AnalyzeScript(&source, 0, length, &sink)))
        return "!analyze";

    // AnalyzeScript does not promise the runs arrive in text order.
    std::sort(sink.runs.begin(), sink.runs.end(),
              [](const ScriptRun& a, const ScriptRun& b) {
                  return a.start < b.start;
              });

    std::string out;
    float pen = 0.0f;
    for (const ScriptRun& run : sink.runs) {
        UINT32 maxGlyphs = 3 * run.length / 2 + 16;
        std::vector<UINT16> clusterMap(run.length);
        std::vector<DWRITE_SHAPING_TEXT_PROPERTIES> textProps(run.length);
        std::vector<UINT16> glyphIndices(maxGlyphs);
        std::vector<DWRITE_SHAPING_GLYPH_PROPERTIES> glyphProps(maxGlyphs);
        UINT32 glyphCount = 0;
        HRESULT hr = E_FAIL;

        // Myanmar clusters expand — one base plus its medials and marks can
        // outgrow the estimate. Grow and retry, as the API asks.
        for (int attempt = 0; attempt < 8; ++attempt) {
            hr = analyzer->GetGlyphs(
                text.c_str() + run.start, run.length, face,
                FALSE /* sideways */, FALSE /* rtl */, &run.analysis,
                locale, nullptr /* number substitution */,
                nullptr /* features */, nullptr /* feature ranges */, 0,
                maxGlyphs, clusterMap.data(), textProps.data(),
                glyphIndices.data(), glyphProps.data(), &glyphCount);
            if (hr != HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER)) break;
            maxGlyphs *= 2;
            glyphIndices.resize(maxGlyphs);
            glyphProps.resize(maxGlyphs);
        }
        if (FAILED(hr)) return "!getglyphs";

        std::vector<FLOAT> advances(glyphCount ? glyphCount : 1);
        std::vector<DWRITE_GLYPH_OFFSET> offsets(glyphCount ? glyphCount : 1);
        hr = analyzer->GetGlyphPlacements(
            text.c_str() + run.start, clusterMap.data(), textProps.data(),
            run.length, glyphIndices.data(), glyphProps.data(), glyphCount,
            face, emSize, FALSE /* sideways */, FALSE /* rtl */,
            &run.analysis, locale,
            nullptr /* features */, nullptr /* feature ranges */, 0,
            advances.data(), offsets.data());
        if (FAILED(hr)) return "!placements";

        for (UINT32 i = 0; i < glyphCount; ++i) {
            // DirectWrite reports an advance per glyph plus an offset from
            // the pen; HarfBuzz reports the same thing as x/y offsets on a
            // running pen. Accumulate so the two are directly comparable.
            // ascenderOffset is positive upwards, as HarfBuzz's y is.
            const float x = pen + offsets[i].advanceOffset;
            const float y = offsets[i].ascenderOffset;
            char buf[64];
            std::snprintf(buf, sizeof buf, "%u@%.0f,%.0f",
                          static_cast<unsigned>(glyphIndices[i]), x, y);
            if (!out.empty()) out += ' ';
            out += buf;
            pen += advances[i];
        }
    }
    return out;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
    if (argc < 3) {
        std::fwprintf(stderr, L"usage: DirectWriteShape <font.ttf> "
                              L"<corpus-utf8.txt> [emSize] [locale]\n");
        return 2;
    }
    const wchar_t* fontPath = argv[1];
    const float emSize = (argc > 3)
        ? static_cast<float>(std::wcstod(argv[3], nullptr)) : 1000.0f;
    // HarfBuzz is driven with language "my" on this corpus; the DirectWrite
    // equivalent is the locale that maps to the same OpenType language
    // system. Both fall back to the default langsys when a font declares
    // none, which is what these fonts do.
    const wchar_t* locale = (argc > 4) ? argv[4] : L"my-MM";

    std::ifstream in(argv[2], std::ios::binary);
    if (!in) {
        std::fwprintf(stderr, L"cannot read %s\n", argv[2]);
        return 2;
    }
    std::string bytes((std::istreambuf_iterator<char>(in)),
                      std::istreambuf_iterator<char>());
    std::wstring all = widen(bytes);

    IDWriteFactory* factory = nullptr;
    HRESULT hr = DWriteCreateFactory(DWRITE_FACTORY_TYPE_ISOLATED,
                                     __uuidof(IDWriteFactory),
                                     reinterpret_cast<IUnknown**>(&factory));
    if (FAILED(hr)) {
        std::fwprintf(stderr, L"DWriteCreateFactory failed: 0x%08lx\n", hr);
        return 2;
    }

    IDWriteFontFile* file = nullptr;
    hr = factory->CreateFontFileReference(fontPath, nullptr, &file);
    if (FAILED(hr)) {
        std::fwprintf(stderr, L"cannot open font %s: 0x%08lx\n", fontPath,
                      static_cast<unsigned long>(hr));
        return 2;
    }
    BOOL supported = FALSE;
    DWRITE_FONT_FILE_TYPE fileType = DWRITE_FONT_FILE_TYPE_UNKNOWN;
    DWRITE_FONT_FACE_TYPE faceType = DWRITE_FONT_FACE_TYPE_UNKNOWN;
    UINT32 faceCount = 0;
    hr = file->Analyze(&supported, &fileType, &faceType, &faceCount);
    if (FAILED(hr) || !supported) {
        std::fwprintf(stderr, L"DirectWrite does not support %s\n", fontPath);
        return 2;
    }
    IDWriteFontFace* face = nullptr;
    hr = factory->CreateFontFace(faceType, 1, &file, 0,
                                 DWRITE_FONT_SIMULATIONS_NONE, &face);
    if (FAILED(hr)) {
        std::fwprintf(stderr, L"CreateFontFace failed: 0x%08lx\n", hr);
        return 2;
    }

    IDWriteTextAnalyzer* analyzer = nullptr;
    hr = factory->CreateTextAnalyzer(&analyzer);
    if (FAILED(hr)) {
        std::fwprintf(stderr, L"CreateTextAnalyzer failed: 0x%08lx\n", hr);
        return 2;
    }

    // Split on newlines here rather than reading line by line, so a lone
    // CR or a trailing newline cannot shift the line numbering the caller
    // pairs its corpus against.
    size_t index = 0, pos = 0;
    while (pos <= all.size()) {
        size_t nl = all.find(L'\n', pos);
        size_t end = (nl == std::wstring::npos) ? all.size() : nl;
        std::wstring line = all.substr(pos, end - pos);
        if (!line.empty() && line.back() == L'\r') line.pop_back();

        // The last line of a file that ends in a newline is empty and not a
        // corpus entry; every other empty line is, and keeps its index.
        if (nl == std::wstring::npos && line.empty() && pos >= all.size())
            break;

        std::string run = shapeLine(analyzer, face, line, emSize, locale);
        if (!run.empty() && run[0] == '!') {
            std::fwprintf(stderr, L"shaping failed on line %zu\n", index + 1);
            return 3;
        }
        std::printf("%zu\t%s\n", index, run.c_str());
        ++index;

        if (nl == std::wstring::npos) break;
        pos = nl + 1;
    }
    return 0;
}
