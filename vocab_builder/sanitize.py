"""Clean HTML before it reaches a card or a web page.

The fields of the cards are built from words.json, grammar.json and sentences from outside
(Tatoeba, AI). Only the markup the build itself writes is kept: a short list of tags with a class,
and links to https addresses. Any other tag is dropped (its text stays, escaped), script and style
blocks are dropped with their content, and every other attribute is removed. Clean input comes out
unchanged.
"""
from html import escape
from html.parser import HTMLParser

TAGS = {"span", "b", "i", "em", "strong", "br", "a", "ul", "ol", "li", "div", "p", "table", "thead",
        "tbody", "tr", "td", "th", "sub", "sup", "u"}
VOID = {"br"}
DROP = {"script", "style", "iframe", "object", "embed", "template"}
ATTRS = {"class", "colspan", "rowspan"}


def safe_url(url):
    """Only https links (and links within the page) are kept."""
    u = (url or "").strip()
    return u if u.lower().startswith("https://") or u.startswith("#") else ""


class _Clean(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self.skip += 1
            return
        if self.skip or tag not in TAGS:
            return
        kept = []
        for k, v in attrs:
            if k in ATTRS and v is not None:
                kept.append(f' {k}="{escape(v, quote=True)}"')
            elif k == "href" and tag == "a" and safe_url(v):
                kept.append(f' href="{escape(safe_url(v), quote=True)}"')
        self.out.append(f"<{tag}{''.join(kept)}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and tag in TAGS and not self.skip:
            self.out.append(f"</{tag}>")

    def handle_endtag(self, tag):
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip and tag in TAGS and tag not in VOID:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data, quote=False))


def clean(html):
    if not html or ("<" not in html and "&" not in html and ">" not in html):
        return html
    p = _Clean()
    p.feed(html)
    p.close()
    return "".join(p.out)
