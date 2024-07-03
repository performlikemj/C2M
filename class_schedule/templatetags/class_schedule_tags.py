# class_schedule/templatetags/class_schedule_tags.py

from django import template
from class_schedule.models import Booking

register = template.Library()

@register.simple_tag(takes_context=True)
def has_booked_session(context, session):
    user = context.request.user
    return Booking.objects.filter(user=user, session=session).exists()
