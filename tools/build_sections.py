#!/usr/bin/env python3
"""
Auto-generate per-subsection pages that DISPLAY external repo README.md content.

Run this BEFORE sphinx-build (e.g., in GitHub Actions).

Source of truth (you edit):
  docs/_chapters/chapter-XX.md

Each chapter file contains blocks like:
  # Chapter 1 — TITLE
  ### 01. Subsection title
  - **Full resource:** [https://github.com/user/repo](https://github.com/user/repo)

This script generates:
  docs/chapter-XX/index.md                 (chapter landing page with toctree)
  docs/sections/chapter-XX/<slug>.md       (one page per subsection, with imported README)
  docs/index.md                             (top-level toctree pointing to chapter indexes)

Notes:
- README import uses:
    https://raw.githubusercontent.com/<user>/<repo>/<branch>/README.md
  with branch fallback: main -> master
- It rewrites common GitHub "blob" image URLs and relative image paths to raw URLs
  so images render correctly in Sphinx.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHAP_SRC = DOCS / "_chapters"
OUT_SECTIONS = DOCS / "sections"

# Accept hyphen, en-dash, em-dash between "Chapter <n>" and title
CHAP_RE = re.compile(r"^#\s+Chapter\s+(\d+)\s+[-–—]\s+(.+?)\s*$", re.M)
# Accept "### 01. Title" or "### 1. Title"
SEC_RE = re.compile(r"^###\s+(\d{1,2})\.\s+(.+?)\s*$", re.M)
URL_RE = re.compile(r"\*\*Full resource:\*\*\s*\[(.*?)\]\((.*?)\)")

MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMG_RE = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.I)


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "section"


def gh_user_repo(url: str):
    u = url.strip()
    if u.endswith(".git"):
        u = u[:-4]
    m = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)\s*$", u)
    if not m:
        return None
    return m.group(1), m.group(2)


def raw_readme_urls(user: str, repo: str):
    return [
        f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{user}/{repo}/master/README.md",
        f"https://raw.githubusercontent.com/{user}/{repo}/main/readme.md",
        f"https://raw.githubusercontent.com/{user}/{repo}/master/readme.md",
    ]


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BioinformaticsCoreDocsBot/1.0 (+https://github.com/asadprodhan)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def blob_to_raw(u: str) -> str:
    """
    Convert:
      https://github.com/<user>/<repo>/blob/<branch>/<path>
    to:
      https://raw.githubusercontent.com/<user>/<repo>/<branch>/<path>
    """
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", u)
    if not m:
        return u
    user, repo, branch, path = m.group(1), m.group(2), m.group(3), m.group(4)
    return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"


def rewrite_images_to_raw(body: str, user: str, repo: str, branch: str) -> str:
    """
    Make images render in Sphinx by:
    - Converting GitHub blob URLs to raw
    - Converting relative image paths to raw base
    """
    raw_base = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/"

    def fix_url(u: str) -> str:
        u = u.strip().strip('"').strip("'")
        # Skip anchors and mailto
        if u.startswith("#") or u.startswith("mailto:"):
            return u
        if u.startswith("data:"):
            return u
        if u.startswith("http://") or u.startswith("https://"):
            return blob_to_raw(u)
        # Relative path -> raw base
        return raw_base + u.lstrip("/")

    # Markdown images
    def md_repl(m):
        alt, url = m.group(1), m.group(2)
        return f"![{alt}]({fix_url(url)})"

    body = MD_IMAGE_RE.sub(md_repl, body)

    # HTML <img src="...">
    def html_repl(m):
        pre, url, post = m.group(1), m.group(2), m.group(3)
        return f"{pre}{fix_url(url)}{post}"

    body = HTML_IMG_RE.sub(html_repl, body)

    return body


def parse_chapter(md: str):
    chap_m = CHAP_RE.search(md)
    if not chap_m:
        return None
    chap_num = int(chap_m.group(1))
    chap_title = chap_m.group(2).strip()

    sections = []
    sec_matches = list(SEC_RE.finditer(md))
    for i, sm in enumerate(sec_matches):
        start = sm.start()
        end = sec_matches[i + 1].start() if i + 1 < len(sec_matches) else len(md)
        block = md[start:end]

        sec_no = int(sm.group(1))
        sec_title = sm.group(2).strip()

        url_m = URL_RE.search(block)
        full_url = url_m.group(2).strip() if url_m else None

        sections.append({"no": sec_no, "title": sec_title, "url": full_url})
    return chap_num, chap_title, sections


def write_section_page(chap_num: int, sec: dict):
    chap_dir = OUT_SECTIONS / f"chapter-{chap_num:02d}"
    chap_dir.mkdir(parents=True, exist_ok=True)

    sec_slug = slugify(f"{sec['no']:02d}-{sec['title']}")
    out = chap_dir / f"{sec_slug}.md"

    url = sec.get("url")
    gh = gh_user_repo(url) if url else None

    # Always give the page a stable, numbered title so the sidebar shows:
    #   01. ...
    #   02. ...
    page_title = f"{sec['no']:02d}. {sec['title']}"

    if not gh:
        # Minimal fallback (no extra banners above)
        lines = [
            f"# {page_title}",
            "",
            "!!! note \"External resource\"",
            "    This item is not a GitHub repo root, so README import is skipped.",
            "    Use the source link below.",
            "",
        ]
        if url:
            lines += [f"{url}", ""]
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return out

    user, repo = gh

    # Try main then master; remember which branch worked for rewriting relative images.
    imported = None
    branch_used = None
    last_err = None

    for candidate in raw_readme_urls(user, repo):
        try:
            imported = fetch_text(candidate).strip()
            # Identify branch from URL
            if f"/{repo}/main/" in candidate:
                branch_used = "main"
            elif f"/{repo}/master/" in candidate:
                branch_used = "master"
            else:
                branch_used = "main"
            break
        except Exception as e:
            last_err = e
            continue

    if imported is None:
        lines = [
            f"# {page_title}",
            "",
            "!!! warning \"Could not import README\"",
            "    Tried: `main` and `master` README.md via raw.githubusercontent.com",
            f"    Error: `{last_err}`",
            "",
        ]
        if url:
            lines += [f"{url}", ""]
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return out

    # Keep README content unchanged, but add a stable numbered title ABOVE it
    # so Sphinx can show subsection numbering in the left sidebar.
    imported = rewrite_images_to_raw(imported, user=user, repo=repo, branch=branch_used or "main")
    out.write_text((f"# {page_title}\n\n" + imported.strip() + "\n"), encoding="utf-8")
    return out


def write_chapter_index(chap_num: int, chap_title: str, section_pages):
    chap_folder = DOCS / f"chapter-{chap_num:02d}"
    chap_folder.mkdir(parents=True, exist_ok=True)
    index = chap_folder / "index.md"

    # ✅ toctree paths must be RELATIVE to docs/chapter-XX/index.md
    # Section pages are under docs/sections/... so we need "../sections/..."
    rels = []
    for p in section_pages:
        rel_from_docs = p.relative_to(DOCS).with_suffix("").as_posix()  # sections/chapter-XX/...
        # Use explicit titles so the left sidebar shows 01/02/03... regardless of the imported README.
        explicit_title = None
        try:
            first_line = p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            explicit_title = first_line if first_line else None
        except Exception:
            explicit_title = None

        target = f"../{rel_from_docs}"  # ../sections/chapter-XX/...
        if explicit_title:
            rels.append(f"{explicit_title} <{target}>")
        else:
            rels.append(target)

    # Chapter title formatting (blue) is handled via CSS class in docs/_static/custom.css
    chap_heading = f"CHAPTER {chap_num:02d}. {chap_title}"

    lines = [
        f"# <span class=\"chapter-title\">{chap_heading}</span>",
        "",
        "> Expand the sidebar to move between sections in this chapter.",
        "",
        "```{toctree}",
        ":maxdepth: 1",
        ":caption: Sections",
        "",
        *rels,
        "```",
        "",
    ]
    index.write_text("\n".join(lines), encoding="utf-8")
    return index


def write_main_index(chapter_indexes):
    """
    Overwrite docs/index.md deterministically so nav is stable.
    """
    index = DOCS / "index.md"
    entries = []
    for p in chapter_indexes:
        rel = p.relative_to(DOCS).with_suffix("").as_posix()
        title = None
        try:
            first = p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            # If the heading contains inline HTML, strip tags for a clean sidebar label.
            first = re.sub(r"<[^>]+>", "", first).strip()
            title = first if first else None
        except Exception:
            title = None

        entries.append(f"{title} <{rel}>" if title else rel)

    lines = [
        "# Bioinformatics Core",
        "",
        "```{toctree}",
        ":maxdepth: 2",
        ":caption: Contents",
        "",
        *entries,
        "```",
        "",
    ]
    index.write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT_SECTIONS.mkdir(parents=True, exist_ok=True)

    chapter_indexes = []
    chap_files = sorted(CHAP_SRC.glob("chapter-*.md"))
    if not chap_files:
        raise SystemExit(f"No chapter files found in {CHAP_SRC}. Expected docs/_chapters/chapter-*.md")

    for chap_file in chap_files:
        md = chap_file.read_text(encoding="utf-8")
        parsed = parse_chapter(md)
        if not parsed:
            print(f"SKIP (chapter header not matched): {chap_file.relative_to(ROOT)}")
            continue
        chap_num, chap_title, sections = parsed

        section_pages = [write_section_page(chap_num, sec) for sec in sections]
        chap_index = write_chapter_index(chap_num, chap_title, section_pages)
        chapter_indexes.append(chap_index)

    chapter_indexes = sorted(chapter_indexes, key=lambda p: p.parent.name)
    write_main_index(chapter_indexes)

    print("Generated chapter indexes:")
    for p in chapter_indexes:
        print(" -", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
