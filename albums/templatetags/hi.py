from django import template
from django.utils.html import mark_safe
from django.contrib.staticfiles import finders
import re

register = template.Library()


@register.simple_tag
def hi(icon_name, style="outline", css_class="h-5 w-5", **kwargs):
    path = finders.find(f"heroicons/{style}/{icon_name}.svg")
    if not path:
        raise ValueError(f"Heroicon '{icon_name}' not found.")
    with open(path) as f:
        svg = f.read()
    if css_class:
        svg = re.sub(r"<svg ", f'<svg class="{css_class}" ', svg, count=1)
    return mark_safe(svg)
