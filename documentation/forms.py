# documentation/forms.py
from django import forms
from .models import UserDocument

class UserDocumentForm(forms.ModelForm):
    class Meta:
        model = UserDocument
        fields = ['submission']
