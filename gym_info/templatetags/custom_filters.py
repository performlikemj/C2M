# gym_info/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def split(value, key):
    """
    Returns the value turned into a list where each item is a string split
    by the key argument.
    """
    return value.split(key)