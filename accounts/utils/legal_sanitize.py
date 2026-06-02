import logging
import re

import bleach

logger = logging.getLogger(__name__)

_DANGEROUS_ELEMENT_RE = re.compile(
    r"<(script|style|iframe|object|embed)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)

ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u",
    "ul", "ol", "li",
    "a", "blockquote", "code", "pre",
    "br", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "*": ["class"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_legal_html(raw: str) -> str:
    if not raw:
        return ""
    pre = _DANGEROUS_ELEMENT_RE.sub("", raw)
    cleaned = bleach.clean(
        pre,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    if len(cleaned) < len(raw):
        logger.warning(
            "legal_document.sanitize.stripped",
            extra={"len_before": len(raw), "len_after": len(cleaned)},
        )
    return cleaned
