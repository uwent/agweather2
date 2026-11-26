"""Markdown to HTML for changelog entries (the page, the admin's preview and the Atom feed).

CommonMark with raw HTML turned off: a `<script>` in an entry comes out as text, so the page's `{@html}` and the
admin's `mark_safe` are safe for anything staff write. Keep `html` off (`test_render` pins it).
"""

from functools import cache

from markdown_it import MarkdownIt


@cache
def _parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False})


def markdown_html(text: str) -> str:
    return _parser().render(text)
