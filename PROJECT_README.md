# Bioinformatics Core (Sphinx + Read the Docs theme)

This repository publishes **Bioinformatics Core** as a book-style documentation site with:

- **Fixed left sidebar** (chapters → expandable subsections)
- **Scrollable right-side content**
- **Auto-import of external GitHub repo `README.md`** into each subsection page

## How authoring works

### 1) Edit chapter source files

Edit these files (they are the *only* manual inputs):

- `docs/_chapters/chapter-01.md`
- `docs/_chapters/chapter-02.md`
- ...
- `docs/_chapters/chapter-15.md`

Each subsection must contain a **repo root** URL like:

- **Full resource:** https://github.com/asadprodhan/GOMCL

The generator will then fetch:

- `https://raw.githubusercontent.com/asadprodhan/GOMCL/main/README.md`
  (and falls back to `master` if needed)

### 2) Generate the site pages

Run:

```bash
python tools/build_sections.py
```

This generates:

- `docs/chapter-XX/index.md` (chapter landing pages with toctree)
- `docs/sections/chapter-XX/*.md` (one page per subsection)

### 3) Build HTML locally (optional)

```bash
sphinx-build -b html docs docs/_build/html
```

Open:

- `docs/_build/html/index.html`

## GitHub Pages deployment

Deployment is handled by GitHub Actions:

- `.github/workflows/deploy-sphinx.yml`

On every push to `main`, it:

1. Installs dependencies (`requirements.txt`)
2. Runs `python tools/build_sections.py`
3. Runs `sphinx-build`
4. Deploys the HTML artifact to GitHub Pages

