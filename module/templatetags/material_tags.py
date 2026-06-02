"""Template filters for material/lesson cards.

Resolves a Module instance (or any object with .file / .url /
.iframe_code attributes) to a short string "kind" so templates can pick
a brand-correct icon + colored chip. Kind buckets:

    pdf   doc   xls   ppt
    image video audio archive
    code  text  link  embed  file

`material_kind`  → kind string used as CSS modifier `.t-<kind>`
`material_icon`  → Font Awesome class for that kind
"""
from __future__ import annotations

import os

from django import template

register = template.Library()


# Extension → kind. Keep lowercase; lookup is `ext.lower()`.
_EXT_KIND = {
    # Documents
    'pdf':  'pdf',
    'doc':  'doc',  'docx': 'doc',  'odt': 'doc',  'rtf': 'doc',
    'xls':  'xls',  'xlsx': 'xls',  'ods': 'xls',  'csv': 'xls',
    'ppt':  'ppt',  'pptx': 'ppt',  'odp': 'ppt',  'key': 'ppt',
    # Media
    'png':  'image', 'jpg':  'image', 'jpeg': 'image', 'gif':  'image',
    'webp': 'image', 'svg':  'image', 'bmp':  'image', 'avif': 'image',
    'mp4':  'video', 'webm': 'video', 'm4v':  'video', 'mov':  'video',
    'ogv':  'video', 'ogg':  'video', 'mkv':  'video', 'avi':  'video',
    'mp3':  'audio', 'wav':  'audio', 'm4a':  'audio', 'aac':  'audio',
    'oga':  'audio', 'opus': 'audio', 'flac': 'audio',
    # Archives
    'zip':  'archive', 'rar': 'archive', '7z': 'archive', 'tar': 'archive',
    'gz':   'archive', 'bz2': 'archive',
    # Code / text
    'py':   'code', 'js':   'code', 'ts':   'code', 'java': 'code',
    'c':    'code', 'cpp':  'code', 'cs':   'code', 'rb':   'code',
    'go':   'code', 'rs':   'code', 'php':  'code', 'html': 'code',
    'css':  'code', 'json': 'code', 'xml':  'code', 'yml':  'code', 'yaml': 'code',
    'txt':  'text', 'md':   'text', 'log':  'text',
}


# Kind → Font Awesome icon class.
_KIND_ICON = {
    'pdf':     'fa-file-pdf',
    'doc':     'fa-file-word',
    'xls':     'fa-file-excel',
    'ppt':     'fa-file-powerpoint',
    'image':   'fa-file-image',
    'video':   'fa-file-video',
    'audio':   'fa-file-audio',
    'archive': 'fa-file-zipper',
    'code':    'fa-file-code',
    'text':    'fa-file-lines',
    'link':    'fa-link',
    'embed':   'fa-code',
    'file':    'fa-file',
}


def _extension(name: str) -> str:
    if not name:
        return ''
    base = os.path.basename(name).split('?', 1)[0].split('#', 1)[0]
    _, ext = os.path.splitext(base)
    return ext.lstrip('.').lower()


@register.filter(name='material_kind')
def material_kind(material) -> str:
    """Resolve a Module-like object to a kind string for CSS/icons.

    Order matters — URLs and custom embed codes are checked before file
    extension so a `url` material doesn't get a generic file icon when
    the model also has a stale file reference.
    """
    if material is None:
        return 'file'
    # iframe_code wins over url so authored embeds (Canva, Slides) show
    # the embed icon even if the field also stores a fallback URL.
    if getattr(material, 'iframe_code', None):
        return 'embed'
    if getattr(material, 'url', None):
        return 'link'
    f = getattr(material, 'file', None)
    name = getattr(f, 'name', '') if f else ''
    if not name:
        return 'file'
    return _EXT_KIND.get(_extension(name), 'file')


@register.filter(name='material_icon')
def material_icon(kind: str) -> str:
    """Font Awesome class name for a kind string."""
    return _KIND_ICON.get(kind, _KIND_ICON['file'])
