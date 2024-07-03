# class_schedule/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from gym_info.models import Trainer
from datetime import timedelta
from django.core.exceptions import ValidationError


class Class(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    max_participants = models.IntegerField(default=10)
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Session(models.Model):
    class_meta = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    recurring = models.BooleanField(default=False, help_text=_("Is this session recurring weekly?"))
    recurrence_end_date = models.DateField(null=True, blank=True, help_text=_("Recur until this date, weekly."))
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')

    def clean(self):
        super().clean()
        # Ensure session time is within 10 am to 10 pm
        if not (10 <= self.start_time.hour < 22 and 10 <= self.end_time.hour <= 22):
            raise ValidationError(_('Session time must be between 10 am and 10 pm.'))

        # Ensure no overlapping sessions for the trainer
        overlapping_sessions = Session.objects.filter(
            trainer=self.trainer,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(id=self.id)
        if overlapping_sessions.exists():
            raise ValidationError(_('Trainer is already booked for another session during this time.'))
        
    def __str__(self):
        trainer_info = f" with {self.trainer.name}" if self.trainer else ""
        return f"{self.class_meta.title} at {self.start_time.strftime('%Y-%m-%d %H:%M')}{trainer_info}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        # Limit the recurrence_end_date to three months from the start_time
        if self.recurring:
            three_months_later = self.start_time + timedelta(days=90)
            if not self.recurrence_end_date or self.recurrence_end_date > three_months_later.date():
                self.recurrence_end_date = three_months_later.date()

        self.clean()
        super().save(*args, **kwargs)

        if self.recurring and is_new:
            current_start_date = self.start_time
            while current_start_date.date() <= self.recurrence_end_date:
                current_start_date += timedelta(weeks=1)
                if current_start_date.date() > self.recurrence_end_date:
                    break
                Session.objects.create(
                    class_meta=self.class_meta,
                    start_time=current_start_date,
                    end_time=current_start_date + (self.end_time - self.start_time),
                    recurring=False,  # Ensure these are not marked as recurring
                    recurrence_end_date=None,  # Clear the recurrence end date
                    trainer=self.trainer
                )

class Booking(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booked_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking for {self.user.username} in {self.session}"
    
class PrivateClassRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_class_requests')
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True)
    requested_date = models.DateTimeField()
    status_choices = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='pending')
    message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Private class request by {self.user.username} for {self.requested_date.strftime('%Y-%m-%d %H:%M:%S')}"