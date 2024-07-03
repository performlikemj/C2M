# Path: gym_info/forms.py

from django import forms
from .models import Trainer, ContactInfo

class TrainerForm(forms.ModelForm):
    class Meta:
        model = Trainer
        fields = ['name', 'bio', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter trainer name'}),
            'bio': forms.Textarea(attrs={'rows': 3}),
            'photo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }
        help_texts = {
            'name': 'Enter the name of the trainer',
            'bio': 'Enter a brief bio of the trainer',
            'photo': 'Upload a photo of the trainer',
        }
        labels = {
            'name': 'Trainer Name',
            'bio': 'Trainer Bio',
            'photo': 'Trainer Photo',
        }

class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ['instagram_url', 'google_maps_url', 'facebook_url', 'tiktok_url']
        widgets = {
            'instagram_url': forms.URLInput(attrs={'class': 'form-control'}),
            'google_maps_url': forms.URLInput(attrs={'class': 'form-control'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'tiktok_url': forms.URLInput(attrs={'class': 'form-control'}),
        }