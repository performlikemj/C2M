# gymApp models
from datetime import datetime, timedelta
import hashlib
import qrcode
from django.conf import settings
from io import BytesIO
from django.core.files import File
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from gym_info.models import Trainer 
from class_schedule.models import Session
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import calendar
import stripe
import uuid
import pytz
import logging
from django.core.exceptions import ValidationError

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


User.add_to_class('temp_email', models.EmailField(blank=True, null=True))

class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    qr_identifier = models.CharField(max_length=64, unique=True, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username} - Gender: {self.get_gender_display()}"

    def delete(self, *args, **kwargs):
        if self.qr_code:
            self.qr_code.delete(save=False)  # Delete QR code image file when the profile is deleted
        super().delete(*args, **kwargs)

    def generate_qr_identifier(self):
        hash_input = (self.user.username + str(self.user.pk) + str(timezone.now())).encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()

    def generate_qr_code(self):
        self.qr_identifier = self.generate_qr_identifier()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_identifier)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_code_{self.user.username}.png'
        filebuffer = InMemoryUploadedFile(
            buffer, None, filename, 'image/png', len(buffer.getvalue()), None)
        self.qr_code.save(filename, filebuffer, save=False)

    def save(self, *args, **kwargs):
        if not self.qr_code or not self.qr_identifier:
            self.generate_qr_code()
        super().save(*args, **kwargs)


class GymVisit(models.Model):
    SESSION_TYPE_CHOICES = [
        ('regular', 'Regular Session'),
        ('personal_training', 'Personal Training Session'),
    ]
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='regular')
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_session_type_display()} - {self.check_in_time.strftime('%Y-%m-%d %H:%M:%S')}"

class MembershipType(models.Model):
    name = models.CharField(max_length=200)
    price_yen_male = models.DecimalField(max_digits=8, decimal_places=2)
    price_yen_female = models.DecimalField(max_digits=8, decimal_places=2)
    included_sessions = models.IntegerField(default=0)
    included_personal_trainings = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='membership_types/', blank=True, null=True)
    stripe_product_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_price_id_male = models.CharField(max_length=200, blank=True, null=True)
    stripe_price_id_female = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.price_yen_male} yen (male), {self.price_yen_female} yen (female) - {self.included_sessions} sessions, {self.included_personal_trainings} personal trainings"

class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='membership')
    membership_type = models.ForeignKey(MembershipType, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    remaining_sessions = models.IntegerField(default=0)
    remaining_personal_trainings = models.IntegerField(default=0)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    def decrement_session(self, session_type):
        if session_type == 'regular':
            self.remaining_sessions = max(0, self.remaining_sessions - 1)
        elif session_type == 'personal_training':
            self.remaining_personal_trainings = max(0, self.remaining_personal_trainings - 1)
        self.save()

    def prorate_sessions(self, join_date):
        # Only prorate for specific membership types
        if self.membership_type and self.membership_type.name.lower() in ['vip', 'premium', 'standard', 'basic']:
            # Get the current year and month
            year = join_date.year
            month = join_date.month

            # Calculate the total days in the month
            total_days_in_month = calendar.monthrange(year, month)[1]

            # Calculate the remaining days in the month from the join date
            remaining_days = total_days_in_month - join_date.day + 1

            # Calculate the daily rate for sessions and personal trainings
            daily_session_rate = self.membership_type.included_sessions / total_days_in_month
            daily_personal_training_rate = self.membership_type.included_personal_trainings / total_days_in_month

            # Calculate the prorated number of sessions and personal trainings
            prorated_sessions = round(daily_session_rate * remaining_days)
            prorated_personal_trainings = round(daily_personal_training_rate * remaining_days)

            # Update the membership with prorated sessions
            self.remaining_sessions = prorated_sessions
            self.remaining_personal_trainings = prorated_personal_trainings
            self.save()

    def is_active(self):
        logger.info(f'Checking if membership is active for user {self.user.username}')

        # Check for trial memberships
        if self.membership_type and self.membership_type.name.lower() == "trial":
            trial_payment = TrialPayment.objects.filter(user=self.user, used=False).first()
            logger.info(f'Trial Payment: {trial_payment}, Remaining Sessions: {self.remaining_sessions}')
            if trial_payment or self.remaining_sessions > 0:
                return True

        # Check for membership date validity
        if self.end_date:
            if timezone.now().date() > self.end_date:
                return False
        elif self.start_date:
            if self.start_date > timezone.now().date():
                return False

        # Check for any ongoing gym visits today
        gym_visits_today = GymVisit.objects.filter(user=self.user, check_in_time__date=timezone.now().date(), check_out_time__isnull=True)
        if gym_visits_today.exists():
            return True

        return self.check_stripe_subscription_status()

    def check_stripe_subscription_status(self):
        if not self.stripe_subscription_id:
            return False

        try:
            subscription = stripe.Subscription.retrieve(self.stripe_subscription_id)
            if subscription.status in ['active', 'trialing']:
                self.end_date = datetime.fromtimestamp(subscription.current_period_end, tz=pytz.UTC).date()
                self.save()
                return True
            else:
                self.end_date = datetime.fromtimestamp(subscription.current_period_end, tz=pytz.UTC).date()
                self.save()
                return False
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False

    def __str__(self):
        return f"{self.user.username}'s membership"

    def check_and_update_period(self):
        if self.stripe_subscription_id:
            subscription = stripe.Subscription.retrieve(self.stripe_subscription_id)
            current_period_end = timezone.datetime.fromtimestamp(subscription.current_period_end)
            
            # Get the last day of the current month
            last_day_of_month = calendar.monthrange(current_period_end.year, current_period_end.month)[1]
            
            if current_period_end.day != last_day_of_month:
                # The period doesn't cover the entire month, so let's update it
                new_period_end = current_period_end.replace(day=last_day_of_month)
                
                try:
                    stripe.Subscription.modify(
                        self.stripe_subscription_id,
                        proration_behavior='none',
                        billing_cycle_anchor=int(new_period_end.timestamp())
                    )
                    
                    self.end_date = new_period_end.date()
                    self.save()
                    
                    return True  # Period was updated
                except stripe.error.StripeError as e:
                    # Log the error
                    logger.error(f"Failed to update Stripe subscription: {e}")
                    return False
        
        return False  # No update was necessary

class PersonalTrainingSession(models.Model):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not self.trainer:
            raise ValidationError(_('A trainer must be assigned for personal training sessions.'))

        session_start = self.session.start_time
        session_end = session_start + timedelta(minutes=self.duration_minutes)

        overlapping_sessions = Session.objects.filter(
            trainer=self.trainer,
            start_time__lt=session_end,
            end_time__gt=session_start,
        ).exclude(id=self.session.id)

        if overlapping_sessions.exists():
            # Change trainer to 'TBD' for regular sessions
            for session in overlapping_sessions:
                if session.class_meta.is_private:
                    raise ValidationError(_('Trainer is already booked for a private session during this time.'))
                else:
                    session.trainer = None
                    session.save()

        # Ensure session time is within 10 am to 10 pm
        if not (10 <= session_start.hour < 22 and 10 <= session_end.hour <= 22):
            raise ValidationError(_('Session time must be between 10 am and 10 pm.'))

class PurchasedTrainingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True)

class TrialPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trial_payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_on = models.DateTimeField(auto_now_add=True)
    used_on = models.DateTimeField(null=True, blank=True)
    discount_credited = models.BooleanField(default=False)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.amount}¥ on {self.paid_on.strftime('%Y-%m-%d %H:%M:%S')} - {'Credited' if self.discount_credited else 'Not Credited'}"

class CancellationReason(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification_token')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Verification token for {self.user.username}"