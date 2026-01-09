import re

from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    if d is None:
        return None
    return d.get(key)


@register.filter
def block_code_from_section(title):
    match = re.search(r"bloque\s+([a-e])\b", title or "", re.IGNORECASE)
    return match.group(1).upper() if match else "UNK"
