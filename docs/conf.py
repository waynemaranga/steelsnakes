import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "steelsnakes"
copyright = "Copyright 2026 Wayne Maranga"
author = "Wayne Maranga"
release = "0.0.1-alpha-9"

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

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
root_doc = "index"

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "deflist",
]
myst_fence_as_directive = ["mermaid"]
myst_heading_anchors = 3

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
napoleon_google_docstring = True
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

mathjax3_config = {
    "tex": {
        "inlineMath": [["\\(", "\\)"], ["$", "$"]],
        "displayMath": [["\\[", "\\]"], ["$$", "$$"]],
        "processEscapes": True,
    },
}

html_theme = "shibuya"
html_title = "steelsnakes"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_baseurl = "https://steelsnakes.readthedocs.io/en/latest/"

html_theme_options = {
    "accent_color": "orange",
    "color_mode": "auto",
    "github_url": "https://github.com/waynemaranga/steelsnakes",
    "globaltoc_expand_depth": 1,
    "nav_links": [
        {"title": "PyPI", "url": "https://pypi.org/project/steelsnakes/"},
        {
            "title": "Discussions",
            "url": "https://github.com/waynemaranga/steelsnakes/discussions",
        },
    ],
}

html_context = {
    "source_type": "github",
    "source_user": "waynemaranga",
    "source_repo": "steelsnakes",
    "source_version": "main",
    "source_docs_path": "/docs/",
}

html_copy_source = False
html_show_sourcelink = False
