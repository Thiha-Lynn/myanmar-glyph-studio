# Community font projects

One folder per font family. A complete family folder contains:

```
projects/<font-name>/
  <FontName>.glyphstudio.json   # the source of truth — drawn in the studio
  <FontName>-Regular.ttf        # the built font (CI builds it; commit it so
                                #   the gallery can serve it)
  proof.png                     # shaping proof sheet from pipeline/proof.py
  OFL.txt                       # the OFL license text with YOUR copyright
                                #   line (copy projects/sample/OFL.txt and
                                #   edit the first lines)
  README.md                     # style owner, style notes, status
```

Only the `.glyphstudio.json` is required to start — open a PR with just
that and CI will build and check it. The TTF, proof and OFL text join when
the font is ready to appear in the [gallery](../web/gallery.html).

Rules of the road:

* **One style owner per family** — see
  [CONTRIBUTING.md](../CONTRIBUTING.md). The owner reviews glyph PRs for
  style fit.
* **License:** everything under this directory is released under the
  [SIL Open Font License 1.1](https://openfontlicense.org). Fonts must
  ship with the OFL text (that is what `OFL.txt` is for).
* **CI checks every PR:** the pipeline build must succeed, fontbakery must
  report no FAILs, and the proof sheet shows reviewers exactly what shaped.

Start from [`sample/`](sample/) to see a complete example.
