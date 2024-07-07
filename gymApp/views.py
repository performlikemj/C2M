# gymApp views
import json
from django.forms import ValidationError
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from .models import (Profile, GymVisit, MembershipType, Membership, 
                     TrialPayment, PersonalTrainingSession, PurchasedTrainingSession, 
                     CancellationReason, EmailVerificationToken)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from .decorators import kiosk_only
from .forms import (CreateUserForm, EditUserProfileForm, UserProfileForm, MembershipForm, 
                    MembershipTypeForm, CancellationReasonForm, ResendVerificationEmailForm)
from documentation.models import UserDocument
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth import logout, login
from datetime import timedelta
import stripe
from django.conf import settings
from functools import wraps
from django.views.decorators.csrf import csrf_exempt
from django.views import View
import logging
from django.urls import reverse
from class_schedule.models import Session, Trainer
import calendar
from datetime import timedelta, datetime, date
import pytz
from dateutil.relativedelta import relativedelta
from .tasks import send_verification_email
import os
from azure.communication.email import EmailClient
from django.views.i18n import set_language as django_set_language


def set_language(request):
    print("set_language view called")
    response = django_set_language(request)
    user_language = request.POST.get('language', None)
    print("Selected language: ", user_language)
    if user_language:
        translation.activate(user_language)
        request.session['django_language'] = user_language
    next_url = request.POST.get('next', '/')
    print("Redirecting to: ", next_url)
    return HttpResponseRedirect(next_url)

logger = logging.getLogger('gymApp')

stripe.api_key = settings.STRIPE_SECRET_KEY

class CustomLoginView(LoginView):
    template_name = 'gymApp/login.html'

    def form_valid(self, form):
        user = form.get_user()
        if user and not user.is_active:
            return redirect('resend_verification_email')
        return super().form_valid(form)

def register(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.temp_email = form.cleaned_data['email']
            user.save()


            # Ensure no duplicate tokens
            EmailVerificationToken.objects.filter(user=user).delete()
            token = EmailVerificationToken.objects.create(user=user)
            
            # Check if the user already has a pending email task
            if not EmailVerificationToken.objects.filter(user=user).exists():
                send_verification_email.delay(user.id, token.token)
            
            messages.success(request, _('Registration successful. Please check your email to verify your account.'))
            return redirect('login')
    else:
        form = CreateUserForm()
    
    return render(request, 'gymApp/register.html', {'form': form})

def resend_verification_email(request):
    if request.method == 'POST':
        form = ResendVerificationEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            try:
                user = User.objects.get(email=email, username=username)
                if not user.is_active:
                    # Ensure no duplicate tokens
                    EmailVerificationToken.objects.filter(user=user).delete()
                    token, created = EmailVerificationToken.objects.get_or_create(user=user)
                    
                    # Check if the user already has a pending email task
                    if not EmailVerificationToken.objects.filter(user=user).exists():
                        send_verification_email.delay(user.id, token.token)
                    
                    messages.success(request, _('If your email address and username are correct, a verification email was sent.'))
                else:
                    messages.info(request, _('Your account is already active. You can log in.'))
            except User.DoesNotExist:
                messages.error(request, _('If your email address and username are correct, a verification email was sent.'))
            return redirect('resend_verification_email')
    else:
        form = ResendVerificationEmailForm()
    
    return render(request, 'gymApp/resend_verification_email.html', {'form': form})


def verify_email(request, token):
    try:
        token = EmailVerificationToken.objects.get(token=token)
        user = token.user
        if user.temp_email:
            user.email = user.temp_email
            user.temp_email = None
        user.is_active = True
        user.save()
        Profile.objects.get_or_create(user=user)
        token.delete()
        messages.success(request, _('Email verified successfully. You can now log in.'))
        return redirect('login')
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, _('Invalid verification link'))
        return redirect('login')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        logger.error(("Invalid payload: {e}").format(e=e))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(("Signature verification failed: {e}").format(e=e))
        return HttpResponse(status=400)

    event_type = event['type']
    logger.info(("Received event: {event_type}").format(event_type=event_type))

    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    elif event_type == 'invoice.updated':
        invoice = event['data']['object']
        handle_invoice_updated(invoice)
    elif event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    elif event_type == 'invoice.created':
        invoice = event['data']['object']
        try:
            handle_invoice_created(invoice)
        except Exception as e:
            logger.error(f"Error handling invoice.created event: {str(e)}")
            return HttpResponse(status=500)
    elif event_type == 'charge.succeeded':
        charge = event['data']['object']
        handle_one_time_payment(charge)
    else:
        logger.info(("Unhandled event type: {event_type}").format(event_type=event_type))

    return HttpResponse(status=200)

def handle_one_time_payment(charge):
    customer_id = charge['customer']
    payment_intent_id = charge['payment_intent']
    user_email = charge['billing_details']['email']
    membership_type_id = charge['metadata'].get('membership_type_id')

    logger.info(("One-time payment completed for customer {customer_id}").format(customer_id=customer_id))
    logger.info(("Payment Intent ID: {payment_intent_id}").format(payment_intent_id=payment_intent_id))
    logger.info(("Customer email: {user_email}").format(user_email=user_email))
    logger.info(("Membership Type ID: {membership_type_id}").format(membership_type_id=membership_type_id))

    if not user_email:
        customer = stripe.Customer.retrieve(customer_id)
        logger.info(("Customer: {customer}").format(customer=customer))
        user_email = customer.email
        logger.info(("Customer email: {user_email}").format(user_email=user_email))

    if user_email and membership_type_id:
        try:
            user = User.objects.get(email=user_email)
            membership, created = Membership.objects.get_or_create(user=user)
            membership_type = MembershipType.objects.get(id=membership_type_id)
            membership.stripe_customer_id = customer_id
            membership.membership_type = membership_type
            membership.remaining_sessions = membership_type.included_sessions
            membership.remaining_personal_trainings = membership_type.included_personal_trainings
            membership.start_date = timezone.now().date()
            if membership_type.name.lower() == 'trial':
                TrialPayment.objects.create(
                    user=user,
                    amount=0,
                    paid_on=timezone.now(),
                    used=False
                )
                membership.end_date = timezone.now().date() + relativedelta(months=1)
                membership.save()
                logger.info(("Membership saved for user {user_email}").format(user_email=user_email))
        except User.DoesNotExist:
            logger.error(("User with email {user_email} does not exist.").format(user_email=user_email))
        except Exception as e:
            logger.error(("Error creating membership for Stripe customer {customer_id} to user: {e}").format(customer_id=customer_id, e=e))

def adjust_invoice_period(subscription_id):
    try:
        # Retrieve the subscription
        subscription = stripe.Subscription.retrieve(subscription_id)
        current_period_end = subscription.current_period_end

        # Convert period_end timestamp to a date
        period_end_date = datetime.fromtimestamp(current_period_end).date()
        year = period_end_date.year
        month = period_end_date.month

        # Find the last day of the month
        last_day_of_month = calendar.monthrange(year, month)[1]
        
        if period_end_date.day != last_day_of_month:
            # Set the new period end date to the last day of the month
            new_period_end = datetime(year, month, last_day_of_month, 23, 59, 59, tzinfo=pytz.UTC)
            
            # Update the subscription with the new billing cycle anchor
            stripe.Subscription.modify(
                subscription_id,
                proration_behavior='none',
                billing_cycle_anchor=int(new_period_end.timestamp())
            )
            logger.info(f"Updated subscription {subscription_id} to end on the last day of the month: {new_period_end}")
        else:
            logger.info(f"Subscription {subscription_id} already ends on the last day of the month.")
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error while adjusting invoice period: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while adjusting invoice period: {str(e)}")
        raise

def handle_checkout_session_completed(session):
    customer_id = session['customer']
    subscription_id = session.get('subscription')
    user_email = session.get('customer_email')
    membership_type_id = session['metadata'].get('membership_type_id')

    logger.info(f"Checkout session completed for customer {customer_id}")
    logger.info(f"Subscription ID: {subscription_id}")
    logger.info(f"Customer email: {user_email}")
    logger.info(f"Membership Type ID: {membership_type_id}")

    if not user_email:
        customer = stripe.Customer.retrieve(customer_id)
        logger.info(f"Customer: {customer}")
        user_email = customer.email
        logger.info(f"Customer email: {user_email}")

    if subscription_id and user_email and membership_type_id:
        try:
            user = User.objects.get(email=user_email)
            membership, created = Membership.objects.get_or_create(user=user)
            membership_type = MembershipType.objects.get(id=membership_type_id)
            membership.stripe_customer_id = customer_id
            membership.stripe_subscription_id = subscription_id
            membership.membership_type = membership_type
            membership.remaining_sessions = membership_type.included_sessions
            membership.remaining_personal_trainings = membership_type.included_personal_trainings
            membership.start_date = timezone.now().date()

            subscription = stripe.Subscription.retrieve(subscription_id)
            current_period_end = subscription['current_period_end']
            membership.end_date = datetime.fromtimestamp(current_period_end).date()

            membership.save()
            logger.info(f"Membership saved for user {user_email}")
            
            # Adjust the invoice period to the last day of the month if necessary
            adjust_invoice_period(subscription_id)

        except User.DoesNotExist:
            logger.error(f"User with email {user_email} does not exist.")
        except Exception as e:
            logger.error(f"Error creating subscription for Stripe customer {customer_id} to user: {e}")

def handle_invoice_created(invoice):
    logger.info(f"Invoice created: {invoice['id']} for customer {invoice['customer']}")
    subscription_id = invoice.get('subscription')
    if subscription_id:
        logger.info(f"Adjusting invoice period for subscription: {subscription_id}")
        adjust_invoice_period(subscription_id)
    else:
        logger.warning(f"No subscription ID found for invoice: {invoice['id']}")

def handle_invoice_updated(invoice):
    customer_id = invoice['customer']
    subscription_id = invoice['subscription']
    logger.info(("Invoice updated for customer {customer_id} and subscription {subscription_id}").format(customer_id=customer_id, subscription_id=subscription_id))
    logger.info(("Status: {status}").format(status=invoice['status']))

def handle_subscription_updated(subscription):
    customer_id = subscription['customer']
    subscription_id = subscription['id']
    cancel_at_period_end = subscription.get('cancel_at_period_end', False)
    canceled_at = subscription.get('canceled_at', None)
    current_period_end = subscription['current_period_end']

    for item in subscription['items']['data']:
        product_id = item['plan']['product']

        logger.info(f"Plan ID: {item['plan']['id']}")
        logger.info(f"Product ID: {product_id}")

        try:
            customer = stripe.Customer.retrieve(customer_id)
            user_email = customer.email
            user = User.objects.get(email=user_email)
            membership, created = Membership.objects.get_or_create(user=user)
            membership.stripe_customer_id = customer_id
            membership.stripe_subscription_id = subscription_id
            membership_type = MembershipType.objects.get(stripe_product_id=product_id)

            if cancel_at_period_end or canceled_at:
                membership.end_date = datetime.fromtimestamp(current_period_end).date()
                logger.info(f"Subscription will be canceled at period end. End date set to {membership.end_date}")
                if canceled_at:
                    membership.canceled_at = datetime.fromtimestamp(canceled_at).date()
                    logger.info(f"Subscription was canceled at {membership.canceled_at}")
            else:
                if membership_type.name.lower() in ['vip', 'premium', 'standard', 'basic']:
                    now = timezone.now()
                    end_of_month = now + relativedelta(day=31)
                    membership.start_date = now.date()
                    membership.end_date = end_of_month.date()
                else:
                    raise ValueError(f"Unknown membership type: {membership_type.name}")

                membership.membership_type = membership_type
                membership.remaining_sessions = membership_type.included_sessions
                membership.remaining_personal_trainings = membership_type.included_personal_trainings
                membership.prorate_sessions(membership.start_date)

            membership.save()
            logger.info("Subscription update handled successfully.")

            # Adjust the invoice period to the last day of the month if necessary
            adjust_invoice_period(subscription_id)

        except User.DoesNotExist:
            logger.error(f"User with email {user_email} does not exist.")
        except Membership.DoesNotExist:
            logger.error(f"Membership for user {user_email} does not exist.")
        except MembershipType.DoesNotExist:
            logger.error(f"Membership type with Stripe product ID {product_id} does not exist.")
        except Exception as e:
            logger.error(f"Error updating subscription for Stripe customer {customer_id}: {e}")


tokyo_tz = pytz.timezone('Asia/Tokyo')

def create_checkout_session(request, membership_type_id):
    user = request.user
    membership_type = get_object_or_404(MembershipType, id=membership_type_id)

    if user.profile.gender == Profile.Gender.MALE:
        price_id = membership_type.stripe_price_id_male
        price_amount = membership_type.price_yen_male
    else:
        price_id = membership_type.stripe_price_id_female
        price_amount = membership_type.price_yen_female

    if not price_id:
        return JsonResponse({'status': 'error', 'message': _('Price ID is missing for the selected membership type.')}, status=400)

    try:
        if membership_type.name.lower() == "trial" and TrialPayment.objects.filter(user=user, used=True).exists():
            messages.error(request, _("You have already used your 'Trial' membership and cannot purchase another."))
            return redirect('select_membership')

        if hasattr(user, 'membership'):
            if user.membership.is_active():
                messages.error(request, _("You already have an active subscription. Please wait until your current subscription ends before purchasing a new one."))
                return redirect('select_membership')
            stripe_customer_id = user.membership.stripe_customer_id
        else:
            customers = stripe.Customer.list(email=user.email)
            if customers.data:
                customer = customers.data[0]
                stripe_customer_id = customer.id
            else:
                full_name = user.get_full_name() or user.username
                try:
                    customer = stripe.Customer.create(email=user.email, name=full_name)
                    stripe_customer_id = customer.id
                except Exception as e:
                    logger.error(f"Failed to create Stripe customer: {e}")
                    stripe_customer_id = ''

        request.session['stripe_customer_id'] = stripe_customer_id

        if membership_type.name.lower() not in ['vip', 'premium', 'standard', 'basic']:
            if membership_type.name.lower() == "trial":
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(price_amount),
                    currency='jpy',
                    customer=stripe_customer_id,
                    description=f'{membership_type.name} Membership',
                    metadata={'membership_type_id': membership_type_id},
                )

                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    payment_intent_data={'metadata': {'membership_type_id': membership_type_id}},
                    customer=stripe_customer_id,
                    success_url=request.build_absolute_uri(reverse('payment_success') + f'?membership_type_id={membership_type_id}'),
                    cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                    mode='payment',
                    line_items=[{
                        'price_data': {
                            'currency': 'jpy',
                            'product_data': {
                                'name': f'{membership_type.name} Membership',
                                'description': f'{membership_type.description}',
                            },
                            'unit_amount': int(price_amount),
                        },
                        'quantity': 1,
                    }],
                    metadata={'membership_type_id': membership_type_id}
                )

                return redirect(checkout_session.url, code=303)
            else:
                return JsonResponse({'status': 'error', 'message': _('Invalid membership type.')}, status=400)
        elif membership_type.name.lower() in ['vip', 'premium', 'standard', 'basic']:
            payment_methods = stripe.PaymentMethod.list(customer=stripe_customer_id, type="card")

            if not payment_methods.data:
                request.session['add_payment_method_redirect'] = request.path
                return redirect('add_payment_method')

            now = datetime.now(tokyo_tz)

            # Calculate the start of the next month as the billing cycle anchor
            next_month = now + relativedelta(months=1)
            first_day_of_next_month = datetime(next_month.year, next_month.month, 1, tzinfo=tokyo_tz)
            billing_cycle_anchor = int(first_day_of_next_month.timestamp())

            subscription_data = {
                'billing_cycle_anchor': billing_cycle_anchor,
                'proration_behavior': 'create_prorations',
                'metadata': {
                    'membership_type_id': membership_type_id,
                    'billing_cycle_day': '1',  # This tells Stripe to bill on the 1st of each month
                },
            }

            # If signing up on the last day of the month, add a one-time charge
            last_day_of_current_month = (now + relativedelta(day=31)).replace(hour=23, minute=59, second=59)
            if now.date() == last_day_of_current_month.date():
                days_in_month = (last_day_of_current_month - (last_day_of_current_month - relativedelta(day=1)).replace(hour=0, minute=0, second=0)).days
                prorated_amount = int(price_amount / days_in_month)
                stripe.InvoiceItem.create(
                    customer=stripe_customer_id,
                    amount=prorated_amount,
                    currency='jpy',
                    description=f"Prorated charge for {now.strftime('%Y-%m-%d')}"
                )

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                customer=stripe_customer_id,
                subscription_data=subscription_data,
                success_url=request.build_absolute_uri(reverse('payment_success') + f'?membership_type_id={membership_type_id}'),
                cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                metadata={'membership_type_id': membership_type_id}
            )

            return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe Error: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': _('An unexpected error occurred.')}, status=500)

@login_required
def payment_success(request):
    messages.success(request, _("Your payment was successful. Welcome to C2M Muay Thai!"))
    return redirect('personal_schedule')

@login_required
@csrf_exempt
def add_payment_method(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        payment_method_id = data.get('payment_method_id')
        user = request.user

        try:
            if hasattr(user, 'membership') and user.membership.stripe_customer_id:
                stripe_customer_id = user.membership.stripe_customer_id
            else:
                customers = stripe.Customer.list(email=user.email)
                if customers.data:
                    customer = customers.data[0]
                    stripe_customer_id = customer.id
                else:
                    full_name = user.get_full_name() or user.username
                    customer = stripe.Customer.create(email=user.email, name=full_name)
                    stripe_customer_id = customer.id
                request.session['stripe_customer_id'] = stripe_customer_id

            logger.info(("Attaching Payment Method {payment_method_id} to Customer {stripe_customer_id}").format(payment_method_id=payment_method_id, stripe_customer_id=stripe_customer_id))
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=stripe_customer_id,
            )

            logger.info(("Setting default Payment Method for Customer {stripe_customer_id}").format(stripe_customer_id=stripe_customer_id))
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )

            redirect_url = reverse('select_membership')
            return JsonResponse({'status': 'success', 'redirect_url': redirect_url})

        except stripe.error.StripeError as e:
            logger.error(("Stripe Error: {error}").format(error=str(e)))
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    else:
        context = {
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        }
        return render(request, 'gymApp/add_payment_method.html', context)

@login_required
def payment_cancel(request):
    messages.info(request, _("Payment was cancelled."))
    redirect_url = reverse('home')
    return redirect(redirect_url)

@login_required
def select_membership(request):
    user = request.user

    if request.method == 'POST' and 'cancel_membership' in request.POST:
        cancellation_form = CancellationReasonForm(request.POST)
        if cancellation_form.is_valid():
            cancellation_reason = cancellation_form.cleaned_data['reason']
            
            try:
                current_membership = Membership.objects.get(user=user)

                CancellationReason.objects.create(user=user, reason=cancellation_reason)

                if hasattr(user, 'membership') and user.membership.stripe_subscription_id:
                    try:
                        now = timezone.now()
                        stripe.Subscription.modify(
                            user.membership.stripe_subscription_id,
                            cancel_at_period_end=True
                        )
                        if current_membership.membership_type.name.lower() in ['vip', 'premium', 'standard', 'basic']:
                            end_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1])
                            current_membership.end_date = end_of_month.date()
                            current_membership.save()
                    except stripe.error.StripeError as e:
                        logger.error(("Failed to cancel Stripe subscription: {error}").format(error=str(e)))
                        messages.error(request, _("Failed to cancel Stripe subscription: {error}").format(error=str(e)))
                        return redirect('select_membership')

                if current_membership.membership_type.name.lower() in ['vip', 'premium', 'standard', 'basic']:
                    messages.success(request, _("Your membership has been cancelled successfully. You can use your remaining sessions until the end of the period."))
                elif current_membership.membership_type.name.lower() == 'trial':
                    messages.success(request, _("Your trial will only expire after you use it."))
                return redirect('select_membership')
            except Membership.DoesNotExist:
                messages.error(request, _("You do not have an active membership to cancel."))
                return redirect('select_membership')
        else:
            messages.error(request, _("Please provide a reason for cancellation."))

    try:
        current_membership = Membership.objects.get(user=user)
    except Membership.DoesNotExist:
        current_membership = None

    membership_types = MembershipType.objects.all()

    used_trial = TrialPayment.objects.filter(user=user, used=True).exists()
    other_membership = Membership.objects.filter(user=user).exclude(membership_type__name__iexact='trial').exists()
    if used_trial or other_membership:
        membership_types = membership_types.exclude(name__iexact="trial")

    cancellation_form = CancellationReasonForm()

    return render(request, 'gymApp/select_membership.html', {
        'current_membership': current_membership,
        'membership_types': membership_types,
        'cancellation_form': cancellation_form
    })

def is_staff(user):
    return user.is_staff

def kiosk_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        kiosk_user = request.user
        if not (kiosk_user.is_authenticated and kiosk_user.username == 'kiosk'):
            return HttpResponseForbidden(_("Access is restricted to kiosk devices only."))
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class CustomLoginView(LoginView):
    template_name = 'gymApp/login.html'

    def form_valid(self, form):
        user = form.get_user()
        if user.is_active:
            return super().form_valid(form)
        else:
            messages.error(self.request, _('Your email is not verified. Please check your inbox.'))
            return self.form_invalid(form)

@login_required
def custom_logout(request):
    logout(request)
    messages.info(request, _('You have successfully logged out.'))
    return redirect('login')

def is_ceo_or_boss(user):
    return user.groups.filter(name='CEO and Boss').exists()

def is_team_member(user):
    return user.groups.filter(name='Team Members').exists()

def is_trainer(user):
    return user.groups.filter(name='Trainers').exists()

@user_passes_test(is_ceo_or_boss)
def list_users(request):
    users = User.objects.filter(is_staff=False).select_related('profile')
    return render(request, 'gymApp/list_users.html', {'users': users})

@user_passes_test(is_ceo_or_boss)
def view_user_documents(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    submissions = UserDocument.objects.filter(user=user).select_related('document')
    return render(request, 'gymApp/view_user_documents.html', {
        'user': user,
        'submissions': submissions
    })

@user_passes_test(is_ceo_or_boss)
def verify_document(request, submission_id):
    submission = get_object_or_404(UserDocument, pk=submission_id)
    if request.method == 'POST':
        submission.verified = 'verified' in request.POST
        submission.save()
        messages.success(request, _("Document '{document_name}' verification status updated.").format(document_name=submission.document.name))
    return redirect('view_user_documents', user_id=submission.user.id)

@login_required
def edit_own_profile(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = EditUserProfileForm(request.POST, request.FILES, instance=user)
        if user_form.is_valid():
            user_form.save()
            if 'temp_email' in user_form.changed_data:
                token, _ = EmailVerificationToken.objects.get_or_create(user=user)
                send_verification_email.delay(user.id, token.token)
                messages.success(request, _('Your profile was updated successfully. Please check your new email to verify the change.'))
            else:
                messages.success(request, _('Your profile was updated successfully.'))
            return redirect('personal_schedule')
        else:
            messages.error(request, _('Profile update failed. Please check the form for errors.'))
    else:
        user_form = EditUserProfileForm(instance=user)

    return render(request, 'gymApp/edit_own_profile.html', {
        'user_form': user_form,
    })

@permission_required('auth.change_user', raise_exception=True)
def edit_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    return handle_form(request, UserProfileForm, 'gymApp/edit_user.html', 'list_users', user, _("User updated successfully."), _("Failed to update user."))

@permission_required('auth.add_user', raise_exception=True)
def add_user(request):
    return handle_form(request, UserProfileForm, 'gymApp/add_user.html', 'list_users', None, _("User added successfully."), _("Failed to add user."))

def handle_form(request, form_class, template_name, success_url, object_instance=None, success_message=_("Operation successful"), error_message=_("Operation failed")):
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=object_instance)
        if form.is_valid():
            form.save()
            messages.success(request, success_message)
            return redirect(success_url)
        else:
            messages.error(request, error_message)
    else:
        form = form_class(instance=object_instance)
    return render(request, template_name, {'form': form})

@permission_required('auth.delete_user', raise_exception=True)
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        try:
            user.delete()
            messages.success(request, _('User deleted successfully.'))
        except Exception as e:
            messages.error(request, _('Error deleting user: {error}').format(error=str(e)))
        return redirect('list_users')
    return render(request, 'gymApp/delete_user.html', {'user': user})

@login_required
@user_passes_test(is_ceo_or_boss)
def manage_memberships(request):
    memberships = Membership.objects.select_related('user', 'membership_type').order_by('-start_date')
    for membership in memberships:
        print(f'membership pk: {membership.pk}')
    return render(request, 'gymApp/manage_memberships.html', {'memberships': memberships})

@user_passes_test(is_ceo_or_boss)
def add_membership(request):
    if request.method == 'POST':
        form = MembershipTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Membership type added successfully.'))
            return redirect('manage_memberships')
        else:
            messages.error(request, _('Failed to add membership type.'))
    else:
        form = MembershipTypeForm()
    
    return render(request, 'gymApp/add_membership.html', {'form': form})

@user_passes_test(is_ceo_or_boss)
def update_membership(request, pk):
    print(f'PK: {pk}')
    membership = get_object_or_404(Membership, pk=pk)
    print(f'Membership: {membership}')
    if request.method == 'POST':
        form = MembershipForm(request.POST, instance=membership)
        if form.is_valid():
            form.save()
            messages.success(request, _('Membership updated successfully.'))
            return redirect('manage_memberships')
        else:
            messages.error(request, _('Failed to update membership.'))
    else:
        form = MembershipForm(instance=membership)
    return render(request, 'gymApp/update_membership.html', {'form': form})

@user_passes_test(is_ceo_or_boss)
def delete_membership(request, pk):
    membership = get_object_or_404(Membership, pk=pk)
    if request.method == 'POST':
        membership.delete()
        messages.success(request, _('Membership deleted successfully.'))
        return redirect('manage_memberships')
    return render(request, 'gymApp/delete_membership.html', {'membership': membership})

@login_required
@kiosk_only
def scan(request):
    return render(request, 'gymApp/check_process.html', {'now': timezone.now()})

@kiosk_only
@login_required
def process_qr_action(request, action, qr_code_data=None):
    try:
        profile = Profile.objects.get(qr_identifier=qr_code_data)
        user = profile.user
        logger.info(f'Profile: {profile}')
        logger.info(f'User ID: {user.id}')

        if action == 'check_in':
            if not user.membership or not user.membership.is_active():
                logger.warning(f'User {user.username} has no active membership.')
                messages.error(request, _('No active membership. Check-in not allowed.'))
                return JsonResponse({'status': 'error', 'message': _('No active membership. Check-in not allowed.')}, status=403)

            membership = Membership.objects.get(user=user)
            sessions = Session.objects.all()
            trainers = Trainer.objects.all()

            return JsonResponse({
                'status': 'success',
                'message': _('Check-in successful.'),
                'user': user.username,
                'membership': {
                    'remaining_sessions': membership.remaining_sessions,
                    'remaining_personal_trainings': membership.remaining_personal_trainings
                },
                'sessions': [{'id': session.id, 'name': session.class_meta.title} for session in sessions],
                'trainers': [{'id': trainer.id, 'name': trainer.name} for trainer in trainers]
            }, status=200)

        elif action == 'check_out':
            logger.info(f'Checking out user {user.username}')
            return check_in_out(request, 'check_out', user=user)

    except Profile.DoesNotExist:
        logger.error(f'Profile not found for QR code data: {qr_code_data}')
        return JsonResponse({'status': 'error', 'message': _('Profile not found')}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}, {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('An unexpected error occurred')})

@kiosk_only
@login_required
def check_in_out(request, action, user=None, session_type=None, session_id=None, trainer_id=None):
    try:
        if not user:
            return JsonResponse({'status': 'error', 'message': _('User not provided.')}, status=400)

        try:
            membership = Membership.objects.get(user=user)
            if action == 'check_in' and not membership.is_active():
                logger.warning(f'User {user.username} has no active membership.')
                return JsonResponse({'status': 'error', 'message': _('No active membership.')}, status=403)

            if action == 'check_in':
                if session_type == 'regular' and membership.remaining_sessions > 0:
                    membership.decrement_session('regular')

                    if membership.membership_type.name.lower() == "trial":
                        trial_payment = TrialPayment.objects.filter(user=user, used=False).first()
                        if trial_payment:
                            trial_payment.used = True
                            trial_payment.used_on = timezone.now()
                            trial_payment.save()
                            logger.info(f'Trial membership for {user.username} marked as used and credited.')

                    gym_visit = GymVisit.objects.create(user=user, session_type='regular')
                elif session_type == 'personal_training' and membership.remaining_personal_trainings > 0:
                    membership.decrement_session('personal_training')
                    session = Session.objects.get(pk=session_id) if session_id else None
                    trainer = Trainer.objects.get(pk=trainer_id) if trainer_id else None
                    gym_visit = GymVisit.objects.create(user=user, session_type='personal_training', session=session, trainer=trainer)
                else:
                    return JsonResponse({'status': 'error', 'message': _('Invalid session type or insufficient sessions.')}, status=400)

                logger.info(f'User {user.username} checked in successfully for {session_type} session.')

                return JsonResponse({'status': 'success', 'message': _('Check-in successful.')})
            elif action == 'check_out':
                gym_visit = GymVisit.objects.filter(user=user, check_out_time__isnull=True).latest('check_in_time')
                gym_visit.check_out_time = timezone.now()
                gym_visit.save()
                if membership.membership_type.name.lower() == "trial":
                    membership.end_date = timezone.now().date()
                    membership.save()
                logger.info(f'User {user.username} checked out successfully.')
                messages.success(request, _('Check-out successful.'))
                return JsonResponse({'status': 'success', 'message': _('Check-out successful.')})

        except Membership.DoesNotExist:
            logger.warning(f'Membership not found for user {user.username}.')
            return JsonResponse({'status': 'error', 'message': _('No active membership.')}, status=403)

    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}, {str(e)}")
        return JsonResponse({'status': 'error', 'message': _('An unexpected error occurred')})

@csrf_exempt
@kiosk_only
@login_required
def select_session_type(request, scan_user):
    logger.info(("Handling {method} request for select_session_type").format(method=request.method))
    if request.method == 'POST':
        data = json.loads(request.body)
        session_type = data.get('session_type')
        session_id = data.get('session_id')
        trainer_id = data.get('trainer_id')

        user = get_object_or_404(User, username=scan_user)
        try:
            response = check_in_out(request, 'check_in', user=user, session_type=session_type, session_id=session_id, trainer_id=trainer_id)
            return response
        except Exception as e:
            logger.error(f"Error in select_session_type: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    logger.warning(_("Method Not Allowed in select_session_type"))
    return JsonResponse({'status': 'error', 'message': _('This method is not allowed')}, status=405)
