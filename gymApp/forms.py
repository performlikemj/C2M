from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.urls import reverse
from .models import Profile, Membership, MembershipType, TrialPayment, EmailVerificationToken
from .tasks import send_verification_email
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'  # Adjust as needed

class EditUserProfileForm(forms.ModelForm):
    new_email = forms.EmailField(label="New Email Address", required=False)
    old_password = forms.CharField(label="Old Password", widget=forms.PasswordInput, required=False)
    new_password1 = forms.CharField(label="New Password", widget=forms.PasswordInput, required=False)
    new_password2 = forms.CharField(label="Confirm New Password", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'new_email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['email'].widget.attrs['readonly'] = True
        if self.instance.temp_email:
            self.fields['email'].initial = self.instance.temp_email
            self.fields['email'].help_text = _("Pending verification")

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')
        if new_email and User.objects.filter(email=new_email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return new_email

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")

        if new_password1 or new_password2:
            if not old_password:
                self.add_error('old_password', _("You must provide your old password to set a new password."))
            if new_password1 and new_password1 != new_password2:
                self.add_error('new_password2', _("The two password fields didn't match."))
            try:
                validate_password(new_password1, self.instance)
            except ValidationError as e:
                self.add_error('new_password1', e)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_email = self.cleaned_data.get('new_email')
        if new_email and new_email != user.email:
            user.temp_email = new_email
            token, created = EmailVerificationToken.objects.get_or_create(user=user)
            send_verification_email.delay(user.id, token.token)

        if self.cleaned_data.get('new_password1'):
            user.set_password(self.cleaned_data['new_password1'])

        if commit:
            user.save()
        return user


class CreateUserForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))
    gender = forms.ChoiceField(
        choices=Profile.Gender.choices,
        label=_("Gender"),
        widget=forms.RadioSelect,
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "gender")

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("A user with this username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile = Profile.objects.create(
                user=user,
                gender=self.cleaned_data['gender']
            )
            profile.save()  # Ensure the profile is saved to generate the QR code and identifier
        return user
    

class UserProfileForm(UserCreationForm):
    TRIAL_ID = 'trial'
    membership_type = forms.ChoiceField(
        widget=forms.RadioSelect,
        label=_("Select your membership type"),
        required=True
    )
    gender = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female')],
        label=_("Gender"),
        widget=forms.RadioSelect,
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'gender')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        membership_choices = [
            (mt.id, f"{mt.name} - {mt.price_yen_male}¥ for men | {mt.price_yen_female}¥ for women, {mt.description}")
            for mt in MembershipType.objects.all()
        ]
        membership_choices.append((self.TRIAL_ID, _("Trial - 4000.00¥, Try out our gym and classes. Become a member and have the trial fee deducted from your first month's membership!")))
        self.fields['membership_type'].choices = membership_choices

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            self.save_m2m()
            # Update or create the Profile
            Profile.objects.update_or_create(
                user=user,
                defaults={'gender': self.cleaned_data['gender']}
            )
            # Handle Membership changes
            if self.cleaned_data['membership_type'] != self.TRIAL_ID:
                membership_type = MembershipType.objects.get(id=self.cleaned_data['membership_type'])
                Membership.objects.update_or_create(
                    user=user,
                    defaults={
                        'membership_type': membership_type,
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + timedelta(days=365),
                        'remaining_sessions': membership_type.included_sessions,
                        'remaining_personal_trainings': membership_type.included_personal_trainings,
                    }
                )
            else:
                # Handle trial membership logic here
                pass
        return user
    

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = '__all__'  # Include all fields

    def __init__(self, *args, **kwargs):
        super(MembershipForm, self).__init__(*args, **kwargs)
        # Set all fields as read-only
        for field in self.fields.values():
            field.disabled = True
        # Enable 'membership_type' and 'start_date' fields
        self.fields['membership_type'].disabled = False
        self.fields['start_date'].disabled = False

    def save(self, commit=True):
        instance = super(MembershipForm, self).save(commit=False)
        # Update only allowed fields
        if commit:
            instance.save(update_fields=['membership_type', 'start_date'])  # Specify fields that should be updated
        return instance


class MembershipTypeForm(forms.ModelForm):
    class Meta:
        model = MembershipType
        fields = ['name', 'price_yen_male', 'price_yen_female', 'included_sessions', 'included_personal_trainings', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['price_yen_male'].widget.attrs.update({'class': 'form-control'})
        self.fields['price_yen_female'].widget.attrs.update({'class': 'form-control'})
        self.fields['included_sessions'].widget.attrs.update({'class': 'form-control'})
        self.fields['included_personal_trainings'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control', 'rows': 3})

class CancellationReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea, required=True, label="Reason for Cancellation")

class ResendVerificationEmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address'})
    )
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username'})
    )