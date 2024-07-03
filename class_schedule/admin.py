# class_schedule/admin.py
from django.contrib import admin
from .models import Class, Session, Booking

# Inline display of Sessions within Class admin view
class SessionInline(admin.TabularInline):
    model = Session
    extra = 1
    show_change_link = True
    fields = ('class_meta', 'start_time', 'end_time', 'trainer', 'recurring', 'recurrence_end_date')
    readonly_fields = ('class_meta',)
    ordering = ('start_time',)

# Inline display of Bookings within Session admin view
class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    show_change_link = True
    fields = ('session', 'user', 'booked_on')
    readonly_fields = ('session', 'user', 'booked_on')
    ordering = ('booked_on',)

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'max_participants', 'is_private')
    list_filter = ('is_private',)
    search_fields = ('title', 'description')
    inlines = [SessionInline]
    ordering = ('title',)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('class_meta', 'start_time', 'end_time', 'recurring', 'trainer')
    list_filter = ('recurring', 'trainer', 'start_time', 'end_time')
    search_fields = ('class_meta__title', 'trainer__name')
    inlines = [BookingInline]
    ordering = ('start_time',)
    fields = ('class_meta', 'start_time', 'end_time', 'trainer', 'recurring', 'recurrence_end_date')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('session', 'user', 'booked_on')
    list_filter = ('booked_on', 'session__class_meta', 'session__trainer')
    search_fields = ('user__username', 'session__class_meta__title', 'session__trainer__name')
    ordering = ('-booked_on',)
    fields = ('session', 'user', 'booked_on')
    readonly_fields = ('session', 'user', 'booked_on')

