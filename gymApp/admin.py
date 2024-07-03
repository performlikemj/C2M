from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, GymVisit, MembershipType, Membership, TrialPayment, PersonalTrainingSession, PurchasedTrainingSession


class MembershipTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price_yen_female', 'price_yen_male', 'included_sessions', 'included_personal_trainings', 'stripe_product_id')
    list_filter = ('price_yen_female', 'price_yen_male', 'included_sessions', 'included_personal_trainings')
    search_fields = ('name',)
    

class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'membership_type', 'start_date', 'end_date', 'remaining_sessions', 'remaining_personal_trainings', 'is_active')
    list_filter = ('membership_type', 'start_date', 'end_date')
    search_fields = ('user__username', 'membership_type__name')
    raw_id_fields = ('user',)

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = "Active Status"


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'view_qr_code')
    search_fields = ('user__username', 'user__email')
    list_filter = ('gender',)

    def view_qr_code(self, obj):
        return format_html('<img src="{}" width="150" height="150" />', obj.qr_code.url if obj.qr_code else '')
    view_qr_code.short_description = "QR Code"


class GymVisitAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_type', 'check_in_time', 'check_out_time')
    list_filter = ('session_type', 'check_in_time', 'check_out_time')
    search_fields = ('user__username', 'session_type')


class TrialPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'paid_on', 'discount_credited', 'used', 'used_on')
    list_filter = ('discount_credited', 'used', 'paid_on', 'used_on')
    search_fields = ('user__username', 'user__email')


class PersonalTrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('membership', 'session', 'duration_minutes', 'trainer')
    list_filter = ('trainer', 'duration_minutes')
    search_fields = ('membership__user__username', 'trainer__name', 'session__name')


class PurchasedTrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'duration_minutes', 'trainer')
    list_filter = ('trainer', 'duration_minutes')
    search_fields = ('user__username', 'trainer__name', 'session__name')


# Register your models here.
admin.site.register(Profile, ProfileAdmin)
admin.site.register(GymVisit, GymVisitAdmin)
admin.site.register(MembershipType, MembershipTypeAdmin)
admin.site.register(Membership, MembershipAdmin)
admin.site.register(TrialPayment, TrialPaymentAdmin)
admin.site.register(PersonalTrainingSession, PersonalTrainingSessionAdmin)
admin.site.register(PurchasedTrainingSession, PurchasedTrainingSessionAdmin)