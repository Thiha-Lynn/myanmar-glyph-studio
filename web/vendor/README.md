# Vendored third-party code

One file, checked in rather than installed — which means no lockfile
mentions it, `npm audit` never sees it, and Dependabot cannot open a PR
for it. So its identity is recorded here and asserted by
`pipeline/tests/test_vendored_js.py`: replacing the file without updating
this table fails the suite.

| File | Package | Version | License |
|---|---|---|---|
| `opentype.min.js` | [opentype.js](https://github.com/opentypejs/opentype.js) | **1.3.4** | MIT |

```
sha256  c0f9c7ca85e18075a8819e5fe2dee6e1d535f9a2269f5314f36cce94a183adba
```

The bytes are identical to `package/dist/opentype.min.js` in the official
npm tarball for that version, which is how the version above was
established — the minified file itself carries no version string:

```bash
curl -sO https://registry.npmjs.org/opentype.js/-/opentype.js-1.3.4.tgz
tar -xzOf opentype.js-1.3.4.tgz package/dist/opentype.min.js | shasum -a 256
```

## What it is used for

`web/js/fontexport.js` only — the studio's one-click draft TTF, built in
the browser. The real build is the Python pipeline; nothing else in the
studio depends on this file, and the fonts in `projects/` were not made
with it.

## Checking it for advisories

It is not in any lockfile, so ask OSV directly:

```bash
curl -s -X POST https://api.osv.dev/v1/query \
  -d '{"package":{"name":"opentype.js","ecosystem":"npm"}}' | jq '.vulns'
```

At the last check (2026-08-23) opentype.js had **no advisories at all**,
at any version.

## Updating it

opentype.js 2.x exists and is not a drop-in: the module shape and several
call signatures changed, and `fontexport.js` would need rewriting against
it. There is no security reason to move — see above — so the pin stays
deliberate. If you do update:

1. take `dist/opentype.min.js` from the npm tarball, not a CDN build;
2. update the version and hash in the table above;
3. run the suite, then export a font from the studio and install it —
   `fontexport.js` is the only caller and the only thing that proves it.
