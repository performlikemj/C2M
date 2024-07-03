# class_schedule/forms.py

from datetime import timedelta
from django import forms
from .models import Class, Session, PrivateClassRequest
from gymApp.models import PersonalTrainingSession
from django.core.exceptions import ValidationError
from datetime import timedelta



class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['title', 'description', 'max_participants', 'is_private']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['class_meta', 'start_time', 'end_time', 'recurring', 'recurrence_end_date', 'trainer']
        widgets = {
            'class_meta': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recurrence_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'trainer': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        recurrence_end_date = cleaned_data.get('recurrence_end_date')
        if recurrence_end_date and start_time:
            if recurrence_end_date > (start_time + timedelta(days=90)).date():
                raise forms.ValidationError("Recurrence end date cannot be more than three months from the start date.")
        return cleaned_data
    
class PrivateClassRequestForm(forms.ModelForm):
    class Meta:
        model = PrivateClassRequest
        fields = ['trainer', 'requested_date', 'message']
        widgets = {
            'requested_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'message': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['requested_date'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean_requested_date(self):
        requested_date = self.cleaned_data.get('requested_date')
        if not requested_date:
            raise ValidationError("Requested date is required.")

        # Check if the day is Thursday
        if requested_date.weekday() == 3:  # Monday is 0, Tuesday is 1, ..., Thursday is 3
            raise ValidationError("Private classes cannot be scheduled on Thursdays.")

        # Check if the time is between 10 am and 10 pm
        if not (10 <= requested_date.hour < 22):
            raise ValidationError("Private classes can only be scheduled between 10 am and 10 pm.")

        return requested_date

    def clean_trainer(self):
        trainer = self.cleaned_data.get('trainer')
        requested_date = self.cleaned_data.get('requested_date')

        if trainer and requested_date:
            end_time = requested_date + timedelta(hours=1)  # Assuming the private class lasts for one hour
            if not trainer.is_available(requested_date, end_time):
                raise ValidationError(f"Trainer {trainer.name} is not available at the requested time.")

            # Check if the trainer has any personal training sessions at the same time
            conflicting_sessions = PersonalTrainingSession.objects.filter(
                trainer=trainer,
                session__start_time__lt=end_time,
                session__end_time__gt=requested_date
            )

            if conflicting_sessions.exists():
                raise ValidationError(f"Trainer {trainer.name} has a conflicting personal training session at the requested time.")

        return trainer