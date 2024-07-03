# your_app/templatetags/my_filters.py

from django import template

register = template.Library()

@register.filter
def make_int(value):
    return int(value)