# gymApp/tasks.py
from datetime import timezone
from celery import shared_task
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from .models import EmailVerificationToken, Membership
import stripe
import logging
from azure.communication.email import EmailClient

logger = logging.getLogger('gymApp')
stripe.api_key = settings.STRIPE_SECRET_KEY

@shared_task
def send_verification_email(user_id, token):
    print(f"Sending verification email to user id {user_id}")
    try:
        user = User.objects.get(pk=user_id)
        subject = 'Verify your email address'
        verification_url = f"{settings.SITE_URL}{reverse('verify_email', args=[token])}"
        message = f"Hi {user.username},\n\nPlease verify your email address by clicking the link below:\n{verification_url}"
        connection_string = settings.AZURE_CONNECTION_STRING
        logger.info(f"Sending verification email to {user.temp_email or user.email} with connection string {connection_string}")
        
        client = EmailClient.from_connection_string(connection_string)
    
        email_message = {
            "senderAddress": "DoNotReply@c2mmuaythai.com",
            "recipients": {
                "to": [{"address": user.temp_email or user.email}],
            },
            "content": {
                "subject": subject,
                "plainText": message,
            }
        }

        logger.info(f"Email message: {email_message}")
        poller = client.begin_send(email_message)
        print(f"Poller: {poller}")
        result = poller.result()
        print(f"Result: {result}")
        
        if result.get('status') == 'Succeeded':
            logger.info(f"Verification email sent to {user.temp_email or user.email}")
        else:
            logger.error(f"Failed to send verification email to {user.temp_email or user.email}. Status: {result.get('status')}")
            logger.error(f"Response: {result}")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist.")
    except Exception as e:
        logger.error(f"An error occurred while sending verification email to user id {user_id}: {e}")
        logger.error(f"Exception details: {e.__class__.__name__}, {e}")

@shared_task
def check_active_subscriptions():
    memberships = Membership.objects.all()
    for membership in memberships:
        if membership.stripe_subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(membership.stripe_subscription_id)
                if subscription.status != 'active':
                    membership.end_date = timezone.now().date()
                    membership.save()
            except stripe.error.StripeError as e:
                # Log the error or handle it appropriately
                print(f"Error checking subscription for {membership.user.email}: {e}")

@shared_task
def check_and_update_membership_periods():
    # Get all active memberships
    active_memberships = Membership.objects.filter(
        end_date__gte=timezone.now().date(),
        stripe_subscription_id__isnull=False
    )
    
    updated_count = 0
    for membership in active_memberships:
        if membership.check_and_update_period():
            updated_count += 1
    
    return f"Updated {updated_count} memberships"