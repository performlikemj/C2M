# gymApp/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import EmailVerificationToken, Profile
from .tasks import send_verification_email

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created:
        token, created = EmailVerificationToken.objects.get_or_create(user=instance)
        send_verification_email.delay(instance.id, token.token)

@receiver(pre_save, sender=Profile)
def email_change_handler(sender, instance, **kwargs):
    if instance.pk:
        old_instance = Profile.objects.get(pk=instance.pk)
        if old_instance.user.email != instance.user.temp_email:
            token, created = EmailVerificationToken.objects.get_or_create(user=instance.user)
            send_verification_email.delay(instance.user.id, token.token)
