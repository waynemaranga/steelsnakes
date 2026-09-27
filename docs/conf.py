# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# Theme: Shibuya (https://shibuya.lepture.com/)
# Markdown: MyST (https://myst-parser.readthedocs.io/)
# API reference: sphinx.ext.autodoc + napoleon (Google-style docstrings)

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "steelsnakes"
copyright = "Copyright © 2026 Wayne Maranga"
author = "Wayne Maranga"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.mathjax",
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- MyST (Markdown) --------------------------------------------------------
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
root_doc = "index"

myst_enable_extensions = [
    "colon_fence",  # ::: fenced directives (admonitions, cards, tabs)
    "dollarmath",  # $inline$ and $$display$$ math
    "deflist",
]
# Fenced ```mermaid code blocks render as the sphinxcontrib-mermaid directive,
# same as they rendered under mkdocs-material's pymdownx.superfences.
myst_fence_as_directive = ["mermaid"]
myst_heading_anchors = 3

# -- Autodoc / Napoleon (Google-style docstrings, matches the old
#    mkdocstrings `docstring_style: google` setting) -------------------------
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Math (mirrors the old docs/javascripts/mathjax.js delimiters) ----------
mathjax3_config = {
    "tex": {
        "inlineMath": [["\\(", "\\)"], ["$", "$"]],
        "displayMath": [["\\[", "\\]"], ["$$", "$$"]],
        "processEscapes": True,
    },
}

# -- HTML output (Shibuya theme) --------------------------------------------
html_theme = "shibuya"
html_title = "steelsnakes"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_favicon = None
html_baseurl = "https://steelsnakes.readthedocs.io/en/latest/"

html_theme_options = {
    "github_url": "https://github.com/waynemaranga/steelsnakes",
    "globaltoc_expand_depth": 1,
    "nav_links": [
        {"title": "PyPI", "url": "https://pypi.org/project/steelsnakes/"},
        {"title": "Discussions", "url": "https://github.com/waynemaranga/steelsnakes/discussions"},
    ],
}

# Powers the theme's "edit this page" links (same intent as mkdocs' edit_uri).
html_context = {
    "source_type": "github",
    "source_user": "waynemaranga",
    "source_repo": "steelsnakes",
    "source_version": "main",
    "source_docs_path": "/docs/",
}

html_copy_source = False
html_show_sourcelink = False
