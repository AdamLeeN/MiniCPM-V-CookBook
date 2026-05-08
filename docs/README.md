# Cookbook documentation site

This directory builds the cookbook's bilingual static site at
**https://opensqz.github.io/MiniCPM-V-CookBook/**.

## Layout

```
docs/
├── README.md            ← this file
├── build_docs.py        ← static-site generator (≈ 600 lines, pure Python)
├── toc.yaml             ← navigation / version / language config
├── index.html           ← root-level redirect → site/{lang}/index.html
├── assets/              ← logos and any future global static assets
│   └── logos/           ← MiniCPM-V, MiniCPM-o, OpenBMB logos
├── pages/               ← markdown that *only* lives in the site
│   ├── index.md         ← landing page
│   ├── framework_matrix.md
│   ├── v4.6/overview.md
│   ├── v4.5/overview.md
│   └── o4.5/overview.md
└── site/                ← BUILD OUTPUT — committed for GitHub Pages
    ├── en/
    ├── zh/
    ├── assets/          (copy of ../assets)
    ├── _pagefind/       (created by `pagefind` when available)
    ├── .nojekyll
    └── index.html       (browser-language redirect)
```

`build_docs.py` reads markdown sources from **anywhere in the repo** based on the
`src:` paths declared in `toc.yaml`. It does **not** copy or duplicate content —
the markdown files under `inference/`, `deployment/`, `quantization/`, etc. are
consumed in place.

## Build / preview locally

```bash
# from repo root
pip install markdown PyYAML

# build static HTML into docs/site/
python docs/build_docs.py

# build + serve on http://localhost:8765
python docs/build_docs.py --serve
```

After the first build, the script prints a translation-sync report listing pages
that exist only in English or only in Chinese, plus pages where the English
version is newer than the Chinese one.

## Adding / editing content

1. Write or update a markdown file anywhere in the repo (the convention is
   that English files end in `.md` and Chinese files end in `_zh.md`).
2. If the page is *new* — add an entry to `docs/toc.yaml` under the right
   version's `nav:` (or under `top_level:` / `shared:`).
3. Re-run `python docs/build_docs.py`.
4. Commit both the source markdown **and** the regenerated `docs/site/`.

The toc structure is:

```yaml
versions:
  - id: v4.6
    label: { en: "MiniCPM-V 4.6", zh: "MiniCPM-V 4.6" }
    badge: latest
    nav:
      - title: { en: Overview, zh: 概览 }
        src:   docs/pages/v4.6/overview.md
        url:   overview                       # → /v4.6/overview.html
      - group: { en: Deployment, zh: 部署 }
        items:
          - title: { en: vLLM, zh: vLLM }
            src: deployment/vllm/minicpm-v4_6_vllm.md   # English source
            url: deployment/vllm                         # → /v4.6/deployment/vllm.html
            # Chinese is auto-detected as ..._zh.md unless `src_zh:` is given
```

## Search (Pagefind)

`build_docs.py` injects a Pagefind UI script tag into every page. The search
box is visible immediately, but it only becomes functional once you've built
the index:

```bash
# one-time install (requires Node.js)
npm i -g pagefind

# rebuild index after every site rebuild
pagefind --site docs/site
```

When `pagefind` is on `$PATH`, `build_docs.py` runs it automatically at the end
of every build. Use `--no-pagefind` to skip.

## Deployment (GitHub Pages)

Configured under repo *Settings → Pages*:

- **Source**: Deploy from a branch
- **Branch**: `main`
- **Folder**: `/docs`

GitHub Pages will then serve the contents of `docs/` at
`https://opensqz.github.io/MiniCPM-V-CookBook/`. The `docs/index.html`
redirects to `docs/site/{lang}/index.html`, which is the actual entry point.

## Conventions and gotchas

- **`> [!NOTE]` admonitions** are translated at build time — Chinese builds
  show 说明 / 提示 / 警告 / 注意 / 重要 instead of Note / Tip / etc.
- **Internal `.md` links** (e.g. `[doc](../llama.cpp/foo.md)`) are rewritten
  to point at the right HTML page in the site, including across language
  switches. Links to files **not** registered in `toc.yaml` are left
  untouched (they will 404 on the site, but still resolve when the file is
  viewed on GitHub).
- **Mermaid blocks** ` ```mermaid ` ` ` are rendered client-side via the
  Mermaid CDN.
- **Code highlighting** uses highlight.js from CDN; no offline asset.
- The script depends only on `markdown` and `PyYAML` from PyPI — both are
  ubiquitous and pre-installed in most data-science environments.

## History

The cookbook used to publish through a Sphinx + Furo site on
`minicpm-o.readthedocs.io`. That stack (`docs/source/`, `.readthedocs.yaml`,
`docs-requirements.txt`, etc.) was retired in favour of this lightweight
build, which lives entirely under `docs/`.

If the legacy `minicpm-o.readthedocs.io` URLs are still in the wild, set
the project on Read the Docs to redirect to the GitHub Pages URL above.
