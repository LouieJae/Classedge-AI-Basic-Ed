"""[Classedge LMS] Template helpers for the reusable list-table shell.

These let `templates/includes/_list_table.html` render any entity's row
purely from a Python `columns` config — no per-entity row template needed.
"""
from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


def _resolve_path(obj, path):
    """[Classedge LMS] Walk a dotted attribute/dict path on an object.

    Supports model attrs, properties, dict keys, and one-level callables.
    Returns "" when the path is empty or any lookup fails — never the bare
    object — so templates can safely chain `|default:` to substitute.
    """
    if obj is None or not path:
        return ""
    cur = obj
    for piece in str(path).split("."):
        if cur is None:
            return ""
        try:
            if isinstance(cur, dict) and piece in cur:
                cur = cur[piece]
            else:
                cur = getattr(cur, piece)
            if callable(cur):
                cur = cur()
        except (AttributeError, KeyError, TypeError):
            return ""
    return cur


@register.filter(name="cl_get")
def cl_get(obj, path):
    """[Classedge LMS] Template filter wrapping ``_resolve_path`` for dotted paths."""
    return _resolve_path(obj, path)


@register.filter(name="cl_format")
def cl_format(template_str, item):
    """[Classedge LMS] Substitute ``{path}`` placeholders in ``template_str``
    with attributes from ``item``. Example:

        "openEditModal({id})" → "openEditModal(42)"
        "/students/{user.id}/" → "/students/7/"
    """
    if not template_str:
        return ""
    out = str(template_str)
    while "{" in out and "}" in out:
        start = out.index("{")
        end = out.index("}", start + 1)
        key = out[start + 1:end]
        value = _resolve_path(item, key)
        out = out[:start] + str(value) + out[end + 1:]
    return out


@register.simple_tag
def cl_action_url(action, item):
    """[Classedge LMS] Build the href for an action dict.

    action keys (any one):
        - url_name + url_arg_attr  → reverse(url_name, args=[item.<arg>])
        - href_template            → string with {path} placeholders
    """
    if not isinstance(action, dict):
        return ""
    if action.get("url_name"):
        arg_attr = action.get("url_arg_attr")
        if arg_attr:
            arg = _resolve_path(item, arg_attr)
            try:
                return reverse(action["url_name"], args=[arg])
            except Exception:
                return ""
        try:
            return reverse(action["url_name"])
        except Exception:
            return ""
    if action.get("href_template"):
        return cl_format(action["href_template"], item)
    return "javascript:void(0);"


@register.simple_tag
def cl_initials(item, first_attr="first_name", last_attr="last_name", name_attr=None, max_chars=2):
    """[Classedge LMS] Render up to ``max_chars`` uppercase initials for an avatar.

    Usage:
        {% cl_initials item "first_name" "last_name" %}
        {% cl_initials item name_attr="name" %}
    """
    if name_attr:
        name = str(_resolve_path(item, name_attr) or "").strip()
        if not name:
            return ""
        parts = name.split()
        initials = "".join(p[0] for p in parts[:max_chars] if p)
        return initials.upper()
    first = str(_resolve_path(item, first_attr) or "").strip()
    last = str(_resolve_path(item, last_attr) or "").strip()
    out = (first[:1] + last[:1]).upper()
    return out or "?"


@register.simple_tag(takes_context=True)
def cl_row_index(context):
    """[Classedge LMS] Sequence index combining forloop + paginator offset."""
    forloop = context.get("forloop") or {}
    page_obj = context.get("page_obj")
    counter = forloop.get("counter", 0) if isinstance(forloop, dict) else getattr(forloop, "counter", 0)
    if page_obj is not None:
        try:
            return counter + page_obj.start_index() - 1
        except (TypeError, AttributeError):
            pass
    return counter
