#!/usr/bin/env python3
"""Cookbook static-site builder.

Reads `docs/toc.yaml` plus the markdown sources scattered across the cookbook
(``inference/``, ``deployment/``, ``quantization/``, ``finetune/``, ``demo/``,
and the page sources under ``docs/pages/``) and emits a self-contained static
site at ``docs/site/{en,zh}/``.

No external dependencies beyond ``markdown`` and ``PyYAML`` (both available on
PyPI). Code highlighting and Mermaid are loaded from CDN at runtime.

Usage:
    python docs/build_docs.py            # build into docs/site/
    python docs/build_docs.py --serve    # build then serve on http://localhost:8765
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import shutil
import socketserver
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import markdown
    import yaml
except ImportError as exc:  # pragma: no cover - bootstrap helper
    missing = exc.name
    print(
        f"\n[build_docs] Missing dependency: {missing}\n"
        "Install with:  pip install markdown PyYAML\n",
        file=sys.stderr,
    )
    sys.exit(1)

from markdown.extensions.toc import TocExtension


# ---------------------------------------------------------------------------
# Paths

THIS = Path(__file__).resolve().parent
REPO = THIS.parent
SITE_DIR = THIS / "site"
ASSETS_DIR = THIS / "assets"
TOC_FILE = THIS / "toc.yaml"
DEFAULT_LANGS = ("en", "zh")


# ---------------------------------------------------------------------------
# Data model

@dataclass
class PageEntry:
    """A single navigable page."""

    slug: str                    # site-relative slug, e.g. "v4.6/deployment/vllm"
    url: str                     # final URL relative to site root, e.g. "v4.6/deployment/vllm.html"
    title: dict[str, str]        # {lang: title}
    src: dict[str, Path]         # {lang: absolute path to markdown source}
    version_id: str | None       # e.g. "v4.6", "shared", or None for top-level
    section: str | None          # section/group label (en) for sidebar grouping
    is_top_level: bool = False
    is_shared: bool = False


@dataclass
class NavGroup:
    """A logical grouping of pages within a sidebar."""

    label: dict[str, str]
    items: list[PageEntry] = field(default_factory=list)


@dataclass
class VersionDef:
    id: str
    label: dict[str, str]
    badge: str | None
    nav: list[Any]               # list of (PageEntry | NavGroup)


# ---------------------------------------------------------------------------
# Loading

def _resolve_src(src_value: str) -> Path:
    """Resolve a `src` field to an absolute path (relative to repo root)."""
    return (REPO / src_value).resolve()


def _zh_for(en_path: Path, override: str | None = None) -> Path | None:
    """Find the Chinese counterpart of an English markdown file.

    The cookbook uses three conventions:
      1. Explicit ``src_zh`` override in toc.yaml.
      2. Sibling file with ``_zh.md`` suffix (most files).
      3. Sibling file with ``_cn.md`` suffix (legacy: dataset_guidance_cn.md).
    Returns ``None`` if no Chinese version exists.
    """
    if override:
        cand = _resolve_src(override)
        return cand if cand.exists() else None

    base = en_path.with_suffix("")  # strip .md
    for suffix in ("_zh.md", "_cn.md"):
        cand = Path(str(base) + suffix)
        if cand.exists():
            return cand
    return None


def load_toc(path: Path) -> tuple[dict, list[VersionDef], list[PageEntry], list[NavGroup]]:
    """Parse toc.yaml and return ``(site_cfg, versions, top_level_pages, shared_groups)``.

    All :class:`PageEntry` objects emitted here have absolute source paths and
    final URL strings already filled in.
    """
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    site_cfg = cfg["site"]

    # ----- top-level pages
    top_level: list[PageEntry] = []
    for raw in cfg.get("top_level", []) or []:
        en_src = _resolve_src(raw["src"])
        zh_src = _zh_for(en_src, raw.get("src_zh"))
        top_level.append(PageEntry(
            slug=raw["url"],
            url=f"{raw['url']}.html",
            title=raw["title"],
            src={"en": en_src} | ({"zh": zh_src} if zh_src else {}),
            version_id=None,
            section=None,
            is_top_level=True,
        ))

    # ----- versions
    versions: list[VersionDef] = []
    for ver_raw in cfg.get("versions", []):
        nav: list[Any] = []
        for entry in ver_raw.get("nav", []):
            if "group" in entry:
                grp = NavGroup(label=entry["group"])
                for item in entry["items"]:
                    grp.items.append(_make_page(item, ver_raw["id"], section_en=entry["group"].get("en")))
                nav.append(grp)
            else:
                nav.append(_make_page(entry, ver_raw["id"], section_en=None))
        versions.append(VersionDef(
            id=ver_raw["id"],
            label=ver_raw["label"],
            badge=ver_raw.get("badge"),
            nav=nav,
        ))

    # ----- shared
    shared: list[NavGroup] = []
    for entry in cfg.get("shared", []) or []:
        if "group" not in entry:
            raise ValueError("entries under `shared:` must be groups")
        grp = NavGroup(label=entry["group"])
        for item in entry["items"]:
            grp.items.append(_make_page(item, "shared", section_en=entry["group"].get("en"), shared=True))
        shared.append(grp)

    return site_cfg, versions, top_level, shared


def _make_page(raw: dict, version_id: str, *, section_en: str | None, shared: bool = False) -> PageEntry:
    en_src = _resolve_src(raw["src"])
    zh_src = _zh_for(en_src, raw.get("src_zh"))

    if version_id == "shared":
        slug = f"shared/{raw['url']}"
    else:
        slug = f"{version_id}/{raw['url']}"

    return PageEntry(
        slug=slug,
        url=f"{slug}.html",
        title=raw["title"],
        src={"en": en_src} | ({"zh": zh_src} if zh_src else {}),
        version_id="shared" if shared else version_id,
        section=section_en,
        is_shared=shared,
    )


# ---------------------------------------------------------------------------
# Page registry — used for cross-page link rewriting

@dataclass
class Registry:
    by_source: dict[Path, PageEntry]
    by_slug: dict[str, PageEntry]
    site_root_links: dict[str, str]  # slug -> default URL (lang-agnostic)

    @classmethod
    def from_pages(cls, pages: list[PageEntry]) -> "Registry":
        by_source: dict[Path, PageEntry] = {}
        by_slug: dict[str, PageEntry] = {}
        for p in pages:
            for src in p.src.values():
                by_source[src.resolve()] = p
            by_slug[p.slug] = p
        site_root_links = {p.slug: p.url for p in pages}
        return cls(by_source=by_source, by_slug=by_slug, site_root_links=site_root_links)


# ---------------------------------------------------------------------------
# Markdown rendering helpers

MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "codehilite",
    "attr_list",
    "def_list",
    TocExtension(permalink=False, toc_depth=3, slugify=lambda v, _: re.sub(r"[^\w\u4e00-\u9fff]+", "-", v.lower()).strip("-")),
]
MD_EXTENSION_CONFIGS = {
    "codehilite": {"guess_lang": False, "css_class": "code"},
}

ADMONITION_RE = re.compile(
    r'^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][^\n]*\n((?:>\s?[^\n]*\n?)+)',
    re.MULTILINE,
)

# Mapping of GitHub admonition kind → display title in current build language.
# We default to English; per-language titles are applied later (see `_localize_admonitions`).
_ADMONITION_TITLES_EN = {
    "note": "Note", "tip": "Tip", "important": "Important",
    "warning": "Warning", "caution": "Caution",
}
_ADMONITION_TITLES_ZH = {
    "note": "说明", "tip": "提示", "important": "重要",
    "warning": "警告", "caution": "注意",
}


def _admonition_replace(m: re.Match[str]) -> str:
    """Convert ``> [!NOTE]\n> body`` blocks into HTML wrappers with the body
    pre-rendered through markdown so inline syntax (links, code) survives.
    """
    kind = m.group(1).lower()
    body_md = "\n".join(line.lstrip("> ").rstrip() for line in m.group(2).splitlines())
    # Render the body separately so inline markdown is processed even though the
    # outer wrapper is already raw HTML.
    body_html = markdown.markdown(
        body_md,
        extensions=["tables", "fenced_code", "attr_list"],
        output_format="html5",
    )
    return (
        f'\n<div class="admonition admonition-{kind}" markdown="0">\n'
        f'<p class="admonition-title">__ADMONITION_TITLE_{kind}__</p>\n'
        f'{body_html}\n'
        f'</div>\n\n'
    )


def _localize_admonitions(html: str, lang: str) -> str:
    titles = _ADMONITION_TITLES_ZH if lang == "zh" else _ADMONITION_TITLES_EN
    for kind, label in titles.items():
        html = html.replace(f"__ADMONITION_TITLE_{kind}__", label)
    return html


def _convert_mermaid(md_text: str) -> str:
    return re.sub(
        r"```mermaid\s*\n(.*?)```",
        lambda m: f'<div class="mermaid">\n{m.group(1).strip()}\n</div>',
        md_text,
        flags=re.DOTALL,
    )


def _strip_md_frontmatter(text: str) -> tuple[str, dict]:
    if not text.startswith("---"):
        return text, {}
    end = text.find("\n---", 3)
    if end == -1:
        return text, {}
    raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        data = {}
    return body, data if isinstance(data, dict) else {}


def render_markdown(md_text: str) -> str:
    md_text = ADMONITION_RE.sub(_admonition_replace, md_text)
    md_text = _convert_mermaid(md_text)
    md = markdown.Markdown(
        extensions=MD_EXTENSIONS,
        extension_configs=MD_EXTENSION_CONFIGS,
        output_format="html5",
    )
    return md.convert(md_text)


# ---------------------------------------------------------------------------
# Link rewriting

REL_LINK_RE = re.compile(r'(?<![!`])\[([^\]]+)\]\(([^)]+)\)')


def rewrite_links(md_text: str, source_path: Path, registry: Registry, lang: str, page: PageEntry) -> str:
    """Rewrite ``[text](relative.md)`` links so that they point at site URLs."""

    def _sub(m: re.Match[str]) -> str:
        text, target = m.group(1), m.group(2).strip()
        # leave anchors / external / mailto / data alone
        if target.startswith(("http://", "https://", "#", "mailto:", "tel:", "data:")):
            return m.group(0)
        # split off anchor
        if "#" in target:
            tgt_path, anchor = target.split("#", 1)
            anchor = "#" + anchor
        else:
            tgt_path, anchor = target, ""
        if not tgt_path:
            return m.group(0)
        # only act on .md / .html paths
        if not (tgt_path.endswith(".md") or tgt_path.endswith(".html")):
            return m.group(0)

        resolved = (source_path.parent / tgt_path).resolve()
        # strip "_zh.md" / "_cn.md" → look up by canonical English source
        canonical = resolved
        for suf in ("_zh.md", "_cn.md"):
            if str(resolved).endswith(suf):
                canonical = Path(str(resolved)[: -len(suf)] + ".md")
                break

        target_page = registry.by_source.get(canonical)
        if not target_page:
            target_page = registry.by_source.get(resolved)
        if not target_page:
            return m.group(0)  # unknown, leave alone

        # produce a path relative to *this* page within the same language
        from_url = f"{lang}/{page.url}"
        to_url = f"{lang}/{target_page.url}"
        new_target = _relpath_url(from_url, to_url) + anchor
        return f"[{text}]({new_target})"

    return REL_LINK_RE.sub(_sub, md_text)


def _relpath_url(from_url: str, to_url: str) -> str:
    """Compute an HTML-friendly relative path between two site-relative URLs."""
    from_dir = os.path.dirname(from_url)
    if not from_dir:
        return to_url
    rel = os.path.relpath(to_url, from_dir)
    # normalize Windows-style paths just in case
    return rel.replace(os.sep, "/")


# ---------------------------------------------------------------------------
# HTML template

CSS = r"""
:root {
  --primary: __PRIMARY__;
  --accent:  __ACCENT__;
  --sidebar-w: 280px;
  --bg: #fff;
  --bg-side: #fafbfc;
  --bg-code: #f6f8fa;
  --c1: #24292f;
  --c2: #57606a;
  --c3: #8b949e;
  --border: #d0d7de;
  --nav-active-bg: rgba(54, 128, 255, .08);
  --nav-active-fg: var(--primary);
  --link: var(--primary);
  --warn-bg: #fff8c5;
  --warn-bd: #d4a72c;
  --note-bg: #ddf4ff;
  --note-bd: #54aeff;
  --tip-bg:  #dafbe1;
  --tip-bd:  #1f883d;
  --important-bg: #fbefff;
  --important-bd: #8250df;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
               "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
  color: var(--c1);
  line-height: 1.65;
  background: var(--bg);
  font-size: 15px;
}
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
img { max-width: 100%; }

/* ---------- top bar ---------- */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; height: 56px; z-index: 100;
  background: #fff;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 20px; gap: 18px;
}
.topbar-brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.topbar-brand img { height: 30px; }
.topbar-brand .brand-text { font-weight: 600; font-size: 15px; color: var(--c1); white-space: nowrap; }
.topbar-search { flex: 1; max-width: 480px; position: relative; }
.topbar-search input {
  width: 100%; padding: 8px 12px 8px 34px; font-size: 14px;
  border: 1px solid var(--border); border-radius: 6px; background: var(--bg-side);
  outline: none; transition: border-color .15s;
}
.topbar-search input:focus { border-color: var(--primary); }
.topbar-search::before {
  content: "🔍"; position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
  font-size: 13px; opacity: .5;
}
.topbar-actions { display: flex; align-items: center; gap: 14px; font-size: 14px; }
.topbar-actions a { color: var(--c2); }
.topbar-actions a:hover { color: var(--primary); }
.topbar-toggle {
  display: none; background: none; border: 1px solid var(--border); border-radius: 6px;
  padding: 4px 10px; font-size: 16px; cursor: pointer;
}

/* ---------- sidebar ---------- */
.sidebar {
  position: fixed; top: 56px; left: 0; bottom: 0; width: var(--sidebar-w);
  overflow-y: auto; background: var(--bg-side); border-right: 1px solid var(--border);
  padding: 16px 0 32px;
  transition: transform .25s;
}
.sidebar-header { padding: 4px 18px 14px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
.sidebar-lang-switch {
  display: inline-block; font-size: 12px; color: var(--primary);
  text-decoration: none; padding: 3px 12px;
  border: 1px solid var(--border); border-radius: 999px;
  transition: background .15s, border-color .15s;
}
.sidebar-lang-switch:hover { background: var(--nav-active-bg); border-color: var(--primary); text-decoration: none; }
.sidebar-lang-switch::before { content: "🌐 "; opacity: .8; margin-right: 2px; }

.version-switcher { padding: 0 18px 12px; }
.version-switcher select {
  width: 100%; padding: 7px 10px; font-size: 14px;
  border: 1px solid var(--border); border-radius: 6px; background: #fff;
  cursor: pointer; outline: none;
}
.version-switcher .badge {
  display: inline-block; margin-left: 6px; padding: 1px 7px; font-size: 11px;
  border-radius: 999px; background: var(--accent); color: #fff;
  vertical-align: middle; font-weight: 600;
}
.nav-list { list-style: none; padding: 4px 12px; }
.nav-list a { display: block; padding: 6px 12px; color: var(--c2); border-radius: 6px;
              font-size: 14px; transition: background .15s, color .15s; }
.nav-list a:hover { background: #ebeff3; color: var(--c1); text-decoration: none; }
.nav-list a.active { background: var(--nav-active-bg); color: var(--nav-active-fg); font-weight: 600; }
.nav-group { margin-top: 8px; }
.nav-group-header {
  padding: 6px 12px; font-size: 11px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--c1); cursor: pointer;
  user-select: none; display: flex; align-items: center; gap: 6px;
  border-radius: 6px; transition: background .15s;
}
.nav-group-header:hover { background: #ebeff3; }
.nav-group-header::before {
  content: ""; width: 0; height: 0;
  border-left: 5px solid var(--c2); border-top: 4px solid transparent; border-bottom: 4px solid transparent;
  transition: transform .2s; transform: rotate(90deg);
}
.nav-group.collapsed .nav-group-header::before { transform: rotate(0); }
.nav-group-children { list-style: none; margin: 2px 0 4px 22px; padding-left: 12px;
                       border-left: 2px solid #e3e7ed;
                       max-height: 800px; overflow: hidden;
                       transition: max-height .25s ease, opacity .2s ease, padding .2s ease;
                       opacity: 1; }
.nav-group.collapsed .nav-group-children { max-height: 0; opacity: 0; }
.nav-group-children a { font-size: 13px; padding: 4px 10px; }

.sidebar-section-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em;
  color: var(--c3); padding: 14px 18px 4px;
}

/* ---------- content ---------- */
.content {
  margin-left: var(--sidebar-w); margin-top: 56px;
  max-width: 920px; padding: 36px 56px 80px;
}
article h1, article h2, article h3, article h4, article h5 {
  font-weight: 600; color: var(--c1); margin: 32px 0 12px; line-height: 1.35;
}
article h1 { font-size: 28px; padding-bottom: 12px; border-bottom: 1px solid var(--border); margin-top: 0; }
article h2 { font-size: 22px; padding-bottom: 8px; border-bottom: 1px solid #eaecef; }
article h3 { font-size: 18px; }
article h4 { font-size: 15px; }
article p, article ul, article ol, article blockquote { margin-bottom: 14px; }
article ul, article ol { padding-left: 24px; }
article li { margin-bottom: 4px; }
article code { background: var(--bg-code); padding: 2px 6px; border-radius: 4px;
                font-size: 13px; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; }
article pre {
  background: var(--bg-code); border: 1px solid var(--border); border-radius: 8px;
  padding: 14px 16px; overflow-x: auto; margin-bottom: 16px;
  font-size: 13.5px; line-height: 1.55;
}
article pre code { background: none; padding: 0; }
article table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 14px; }
article th, article td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; vertical-align: top; }
article th { background: var(--bg-code); font-weight: 600; }
article tr:nth-child(even) { background: #fafbfc; }
article hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
article blockquote {
  border-left: 4px solid var(--primary); padding: 6px 16px; color: var(--c2);
  background: var(--bg-side); border-radius: 0 6px 6px 0;
}

article .admonition {
  border-radius: 8px; padding: 12px 18px; margin: 16px 0;
  border-left: 4px solid var(--note-bd); background: var(--note-bg);
}
article .admonition .admonition-title {
  font-weight: 700; margin: 0 0 4px; font-size: 13px; text-transform: uppercase;
  letter-spacing: .04em; color: var(--c1);
}
article .admonition-warning  { border-left-color: var(--warn-bd); background: var(--warn-bg); }
article .admonition-caution  { border-left-color: var(--warn-bd); background: var(--warn-bg); }
article .admonition-tip      { border-left-color: var(--tip-bd);  background: var(--tip-bg); }
article .admonition-important{ border-left-color: var(--important-bd); background: var(--important-bg); }

article .mermaid { margin: 16px auto; text-align: center; }
article .toc { background: var(--bg-side); border: 1px solid var(--border); border-radius: 8px; padding: 12px 18px; margin: 16px 0; }
article .toc > ul { padding-left: 20px; margin: 0; }

article a.headerlink { margin-left: 6px; opacity: 0; }
article :hover > a.headerlink { opacity: .5; }

footer.page-footer { margin-top: 60px; padding-top: 16px; border-top: 1px solid var(--border);
                     color: var(--c2); font-size: 13px; display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; }
footer.page-footer a { color: var(--c2); }
footer.page-footer a:hover { color: var(--primary); }

/* ---------- responsive ---------- */
@media (max-width: 900px) {
  .topbar-toggle { display: inline-block; }
  .topbar-search { display: none; }
  .sidebar { transform: translateX(-100%); box-shadow: 2px 0 12px rgba(0,0,0,.08); }
  .sidebar.open { transform: translateX(0); }
  .content { margin-left: 0; padding: 28px 22px 60px; }
}
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<title>{title} — {site_title}</title>
<link rel="icon" type="image/png" href="{logo_root}assets/logos/openbmb.png">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11/styles/github.min.css">
<style>{css}</style>
</head>
<body data-version="{version_id}" data-lang="{lang}" data-slug="{slug}">

<header class="topbar">
  <button class="topbar-toggle" aria-label="Toggle navigation" onclick="toggleSidebar()">☰</button>
  <a class="topbar-brand" href="{home_href}">
    <img src="{logo_root}assets/logos/minicpmv.png" alt="MiniCPM-V">
    <span class="brand-text">{site_title}</span>
  </a>
  <div class="topbar-search">
    <input type="search" placeholder="{search_placeholder}" id="pagefind-search">
  </div>
  <nav class="topbar-actions">
    {action_links}
  </nav>
</header>

<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <a class="sidebar-lang-switch" href="{lang_switch_href}" rel="alternate" hreflang="{other_lang}">{other_lang_label}</a>
  </div>
  {sidebar_html}
</aside>

<main class="content" id="content">
  <article>{body}</article>

  <footer class="page-footer">
    <span>{footer_left}</span>
    <span>{footer_right}</span>
  </footer>
</main>

<script>
  // ----- core UI behaviour (must run even if external CDNs are blocked) -----
  function toggleSidebar() {{
    document.getElementById('sidebar').classList.toggle('open');
  }}

  document.querySelectorAll('.nav-group-header').forEach(h => {{
    h.addEventListener('click', () => h.parentElement.classList.toggle('collapsed'));
  }});

  // Close sidebar when clicking a link on mobile.
  document.querySelectorAll('.sidebar a').forEach(a => {{
    a.addEventListener('click', () => {{
      if (window.innerWidth <= 900) {{
        document.getElementById('sidebar').classList.remove('open');
      }}
    }});
  }});

  // Version switcher dropdown.
  const verSel = document.getElementById('version-switcher-select');
  if (verSel) {{
    verSel.addEventListener('change', e => {{
      const target = e.target.value;
      if (target) window.location.href = target;
    }});
  }}
</script>

<!-- Optional enhancements below. Wrapped so a CDN hiccup never breaks the
     interactive sidebar / version switcher above. -->
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11/lib/core.min.js" onerror="window.__hljsBlocked=true"></script>
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11/lib/common.min.js" onerror="window.__hljsBlocked=true"></script>
<script>
  try {{ if (typeof hljs !== 'undefined') hljs.highlightAll(); }} catch (e) {{ console.warn('hljs failed:', e); }}
</script>
<script type="module">
  try {{
    const m = await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs');
    m.default.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
  }} catch (e) {{ console.warn('mermaid failed:', e); }}
</script>
{search_script}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Sidebar rendering

def render_sidebar(
    *,
    lang: str,
    site_cfg: dict,
    versions: list[VersionDef],
    top_level: list[PageEntry],
    shared: list[NavGroup],
    current: PageEntry,
    current_version: str | None,
) -> str:
    """Render the sidebar HTML for a given page."""

    # Always show: top-level pages → version switcher → version nav → shared nav.
    out: list[str] = []

    # Top-level navigation
    out.append('<ul class="nav-list">')
    for p in top_level:
        active = " active" if p.slug == current.slug else ""
        url = _link_for_page(p, current, lang)
        title = p.title.get(lang, p.title["en"])
        out.append(f'  <li><a class="{active.strip()}" href="{url}">{title}</a></li>')
    out.append('</ul>')

    # For top-level pages (Home / Framework Matrix) the page has no version of
    # its own, but we still want a fully populated sidebar (otherwise the home
    # page looks empty compared to deeper pages). Fall back to the default
    # version's nav in that case.
    nav_version_id = current_version
    if nav_version_id in (None, "shared"):
        default_id = site_cfg.get("default_version") or (versions[0].id if versions else None)
        nav_version_id = default_id

    # Version switcher
    out.append(f'<div class="sidebar-section-title">{"Version" if lang == "en" else "版本"}</div>')
    out.append('<div class="version-switcher">')
    out.append('  <select id="version-switcher-select">')
    for v in versions:
        # determine target URL when switching to this version
        target_slug = _equivalent_slug(current, v.id)
        target = _href_to_slug(current, target_slug, lang)
        selected = " selected" if v.id == nav_version_id else ""
        label = v.label.get(lang, v.label["en"])
        badge = f' [{v.badge}]' if v.badge else ""
        out.append(f'    <option value="{target}"{selected}>{label}{badge}</option>')
    out.append('  </select>')
    out.append('</div>')

    for v in versions:
        if v.id != nav_version_id:
            continue
        out.append('<ul class="nav-list">')
        for entry in v.nav:
            if isinstance(entry, NavGroup):
                out.append(_render_group(entry, current, lang))
            else:
                out.append(_render_leaf(entry, current, lang))
        out.append('</ul>')

    # Shared navigation
    if shared:
        out.append(f'<div class="sidebar-section-title">{"Cross-version" if lang == "en" else "跨版本"}</div>')
        out.append('<ul class="nav-list">')
        for grp in shared:
            out.append(_render_group(grp, current, lang))
        out.append('</ul>')

    return "\n".join(out)


def _render_leaf(p: PageEntry, current: PageEntry, lang: str) -> str:
    active = " active" if p.slug == current.slug else ""
    url = _link_for_page(p, current, lang)
    title = p.title.get(lang, p.title["en"])
    return f'<li><a class="{active.strip()}" href="{url}">{title}</a></li>'


def _render_group(grp: NavGroup, current: PageEntry, lang: str) -> str:
    label = grp.label.get(lang, grp.label.get("en", ""))
    children_html = "\n".join(_render_leaf(p, current, lang) for p in grp.items)
    # All groups start expanded so visitors immediately see every recipe under
    # Inference / Deployment / Quantization / etc. The arrow caret still
    # indicates click-to-collapse, but no nav item is hidden by default.
    return (
        f'<li class="nav-group">'
        f'<div class="nav-group-header">{label}</div>'
        f'<ul class="nav-group-children">{children_html}</ul>'
        f'</li>'
    )


def _link_for_page(p: PageEntry, current: PageEntry, lang: str) -> str:
    return _relpath_url(f"{lang}/{current.url}", f"{lang}/{p.url}")


def _href_to_slug(current: PageEntry, slug: str, lang: str) -> str:
    return _relpath_url(f"{lang}/{current.url}", f"{lang}/{slug}.html")


def _equivalent_slug(current: PageEntry, target_version: str) -> str:
    """When switching version, try to land on the same logical page."""
    if current.is_top_level or current.is_shared:
        # top-level pages are version-agnostic; just navigate to that version's overview
        return f"{target_version}/overview"
    if current.version_id == target_version:
        return current.slug
    # strip version prefix and try same path under target version
    rest = current.slug.split("/", 1)[1] if "/" in current.slug else "overview"
    return f"{target_version}/{rest}"


# ---------------------------------------------------------------------------
# Build

@dataclass
class BuildContext:
    site_cfg: dict
    versions: list[VersionDef]
    top_level: list[PageEntry]
    shared: list[NavGroup]
    registry: Registry
    site_dir: Path

    @property
    def all_pages(self) -> list[PageEntry]:
        out = list(self.top_level)
        for v in self.versions:
            for entry in v.nav:
                if isinstance(entry, NavGroup):
                    out.extend(entry.items)
                else:
                    out.append(entry)
        for grp in self.shared:
            out.extend(grp.items)
        return out


def build_page(ctx: BuildContext, page: PageEntry, lang: str) -> str | None:
    src = page.src.get(lang)
    fallback_notice = ""
    if not src:
        # only one language exists — fall back to whatever we have
        if not page.src:
            return None
        other_lang = next(iter(page.src.keys()))
        src = page.src[other_lang]
        if lang == "zh" and other_lang == "en":
            fallback_notice = (
                '<div class="admonition admonition-note"><p class="admonition-title">提示</p>\n'
                '<p>该文档暂时只有英文版本，正在翻译中。</p></div>\n'
            )
        elif lang == "en" and other_lang == "zh":
            fallback_notice = (
                '<div class="admonition admonition-note"><p class="admonition-title">Note</p>\n'
                '<p>An English translation of this page is in progress.</p></div>\n'
            )

    md_text = src.read_text(encoding="utf-8")
    md_text, _ = _strip_md_frontmatter(md_text)
    md_text = rewrite_links(md_text, src, ctx.registry, lang, page)
    body = fallback_notice + render_markdown(md_text)
    body = _localize_admonitions(body, lang)

    site_cfg = ctx.site_cfg
    site_title = site_cfg["title"].get(lang, site_cfg["title"]["en"])
    title = page.title.get(lang, page.title["en"])

    # Compute paths
    out_url = f"{lang}/{page.url}"

    # Home href: relative to current page
    home_href = _relpath_url(out_url, f"{lang}/index.html")

    # Logo root: where assets/ lives, relative to current page's directory.
    # out_url has form "{lang}/{slug}.html" — number of leading "../" needed
    # equals the number of "/"s in out_url.
    depth = out_url.count("/")
    logo_root = "../" * depth if depth else ""

    # Language switch link: same slug, other language
    other_lang = "zh" if lang == "en" else "en"
    if other_lang in page.src:
        switch_target = f"{other_lang}/{page.url}"
    else:
        # other language doesn't have this page — fall back to other language's home
        switch_target = f"{other_lang}/index.html"
    lang_switch_href = _relpath_url(out_url, switch_target)
    other_lang_label = "中文" if other_lang == "zh" else "English"

    # Action links from site config
    action_links_parts = []
    for link in site_cfg.get("links", []):
        label = link["label"].get(lang, link["label"].get("en", ""))
        action_links_parts.append(f'<a href="{link["url"]}" target="_blank" rel="noopener">{label}</a>')
    action_links_html = "\n    ".join(action_links_parts)

    sidebar_html = render_sidebar(
        lang=lang,
        site_cfg=site_cfg,
        versions=ctx.versions,
        top_level=ctx.top_level,
        shared=ctx.shared,
        current=page,
        current_version=page.version_id,
    )

    description = page.title.get(lang, page.title["en"])
    if site_cfg.get("tagline", {}).get(lang):
        description = description + " — " + site_cfg["tagline"][lang]

    footer_left = (
        f'© OpenBMB · <a href="{site_cfg["repo"]}">GitHub</a>'
        if lang == "en"
        else f'© OpenBMB · <a href="{site_cfg["repo"]}">GitHub 仓库</a>'
    )
    footer_right = (
        f'Built with <code>build_docs.py</code>'
        if lang == "en"
        else f'由 <code>build_docs.py</code> 自动生成'
    )

    css = (CSS
           .replace("__PRIMARY__", site_cfg["brand"]["primary"])
           .replace("__ACCENT__",  site_cfg["brand"]["accent"]))

    search_script = (
        '<link href="https://cdn.jsdelivr.net/npm/@pagefind/default-ui@1/css/ui.css" rel="stylesheet">\n'
        '<script src="https://cdn.jsdelivr.net/npm/@pagefind/default-ui@1/npm/index.js"></script>\n'
        '<script>\n'
        '  // Pagefind is loaded from a relative path emitted at build time.\n'
        '  const inp = document.getElementById("pagefind-search");\n'
        '  if (inp) {\n'
        '    inp.addEventListener("focus", function once() {\n'
        '      inp.removeEventListener("focus", once);\n'
        '      const root = inp.parentElement;\n'
        '      const div = document.createElement("div"); div.id = "search"; root.appendChild(div);\n'
        '      new PagefindUI({ element: "#search", showSubResults: true });\n'
        '    });\n'
        '  }\n'
        '</script>\n'
    )

    return PAGE_TEMPLATE.format(
        html_lang="zh-CN" if lang == "zh" else "en",
        title=title,
        site_title=site_title,
        description=description,
        css=css,
        version_id=page.version_id or "",
        lang=lang,
        slug=page.slug,
        logo_root=logo_root,
        home_href=home_href,
        search_placeholder="搜索文档…" if lang == "zh" else "Search docs…",
        action_links=action_links_html,
        other_lang=other_lang,
        other_lang_label=other_lang_label,
        lang_switch_href=lang_switch_href,
        sidebar_html=sidebar_html,
        body=body,
        footer_left=footer_left,
        footer_right=footer_right,
        search_script=search_script,
    )


def write_site(ctx: BuildContext, langs: tuple[str, ...] = DEFAULT_LANGS) -> dict[str, int]:
    site = ctx.site_dir
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)

    # Copy static assets
    target_assets = site / "assets"
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, target_assets)

    counts = {lang: 0 for lang in langs}
    for lang in langs:
        for page in ctx.all_pages:
            html = build_page(ctx, page, lang)
            if html is None:
                continue
            out_path = site / lang / page.url
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(html, encoding="utf-8")
            counts[lang] += 1

    # Default-language redirect at site root
    default_lang = ctx.site_cfg.get("default_lang", "en")
    redirect = f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{ctx.site_cfg["title"]["en"]}</title>
<meta http-equiv="refresh" content="0; url=./{default_lang}/index.html">
<script>
  // Honor browser language preference (Accept-Language is not exposed to JS,
  // navigator.language is the closest thing).
  (function () {{
    var lang = (navigator.language || 'en').toLowerCase();
    var target = lang.startsWith('zh') ? 'zh' : '{default_lang}';
    location.replace('./' + target + '/index.html');
  }})();
</script>
</head><body>
<p>Redirecting… <a href="./{default_lang}/index.html">click here</a> if not redirected.</p>
</body></html>
'''
    (site / "index.html").write_text(redirect, encoding="utf-8")

    # GitHub Pages should not run jekyll
    (site / ".nojekyll").write_text("", encoding="utf-8")

    return counts


# ---------------------------------------------------------------------------
# Sync warnings

def sync_warnings(pages: list[PageEntry]) -> list[str]:
    out = []
    for p in pages:
        if "en" in p.src and "zh" in p.src:
            en_t = p.src["en"].stat().st_mtime
            zh_t = p.src["zh"].stat().st_mtime
            if en_t > zh_t + 60:  # >1 min newer
                out.append(f"  [stale-zh] {p.slug}: en is {(en_t - zh_t) / 86400:.1f} days newer than zh")
        elif "en" in p.src and "zh" not in p.src:
            out.append(f"  [missing-zh] {p.slug}")
        elif "zh" in p.src and "en" not in p.src:
            out.append(f"  [missing-en] {p.slug}")
    return out


# ---------------------------------------------------------------------------
# Pagefind

def run_pagefind(site_dir: Path) -> bool:
    """Run pagefind to build the search index. Returns True if successful."""
    import subprocess

    candidates = ["pagefind", "npx pagefind"]
    for cmd in candidates:
        try:
            result = subprocess.run(
                cmd.split() + ["--site", str(site_dir)],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"[pagefind] indexed via `{cmd}`")
                return True
        except FileNotFoundError:
            continue
    return False


# ---------------------------------------------------------------------------
# CLI

def main() -> None:
    parser = argparse.ArgumentParser(description="Build the MiniCPM-V & o cookbook docs site")
    parser.add_argument("--toc", default=str(TOC_FILE), help="path to toc.yaml")
    parser.add_argument("--out", default=str(SITE_DIR), help="output directory")
    parser.add_argument("--no-pagefind", action="store_true", help="skip building the search index")
    parser.add_argument("--serve", action="store_true", help="serve the built site after building")
    parser.add_argument("--port", type=int, default=8765, help="port for --serve")
    args = parser.parse_args()

    site_cfg, versions, top_level, shared = load_toc(Path(args.toc))

    all_pages: list[PageEntry] = list(top_level)
    for v in versions:
        for entry in v.nav:
            if isinstance(entry, NavGroup):
                all_pages.extend(entry.items)
            else:
                all_pages.append(entry)
    for grp in shared:
        all_pages.extend(grp.items)

    # Sanity check: every English source must exist
    missing = [str(p.src.get("en")) for p in all_pages if "en" in p.src and not p.src["en"].exists()]
    if missing:
        print("[error] missing source files:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(2)

    registry = Registry.from_pages(all_pages)
    ctx = BuildContext(
        site_cfg=site_cfg,
        versions=versions,
        top_level=top_level,
        shared=shared,
        registry=registry,
        site_dir=Path(args.out),
    )

    print(f"[build] writing to {ctx.site_dir}")
    counts = write_site(ctx)
    total = sum(counts.values())
    for lang, n in counts.items():
        print(f"  {lang}: {n} pages")
    print(f"[build] {total} pages total")

    warnings = sync_warnings(all_pages)
    if warnings:
        print(f"\n[sync] {len(warnings)} translation issues:")
        for w in warnings[:30]:
            print(w)
        if len(warnings) > 30:
            print(f"  ...and {len(warnings) - 30} more")

    if not args.no_pagefind:
        if not run_pagefind(ctx.site_dir):
            print("[pagefind] not installed — skip. Install with: npm i -g pagefind")
            print("[pagefind] (search box will be visible but inert until indexed)")

    if args.serve:
        os.chdir(ctx.site_dir)
        with socketserver.TCPServer(("", args.port), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"\n[serve] http://localhost:{args.port}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
