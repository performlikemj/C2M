# gym_info/admin.py

from django.contrib import admin
from .models import Trainer, ContactInfo
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
import logging

logger = logging.getLogger(__name__)

class TrainerInline(admin.StackedInline):
    model = Trainer
    can_delete = False
    verbose_name_plural = 'trainer'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (TrainerInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'bio')
    search_fields = ('name', 'user__username')
    list_filter = ('user__is_staff',)

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"Error saving model {obj}: {e}")
            raise

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('instagram_url', 'google_maps_url', 'facebook_url', 'tiktok_url')
