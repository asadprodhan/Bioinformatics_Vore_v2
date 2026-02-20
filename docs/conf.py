# -- Project information -----------------------------------------------------

project = "Bioinformatics Core"
author = "Dr Asad Prodhan"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]

# IMPORTANT:
# - _chapters contains SOURCE markdown only (do not render)
# - sections/ and chapter-XX/ MUST be rendered
exclude_patterns = [
    "_build",
    "_chapters/**",
]

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"

# Custom styling (chapter title blue)
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    # CRITICAL for your layout
    "collapse_navigation": False,   # keep tree expanded
    "navigation_depth": 4,          # chapters → subsections
    "titles_only": False,           # show subsection titles
    "sticky_navigation": True,
}

# Optional but recommended
html_show_sourcelink = True
html_show_sphinx = False
