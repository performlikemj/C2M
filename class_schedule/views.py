from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.utils.translation import gettext as _
from .models import Class, Session, Booking, PrivateClassRequest
from gymApp.models import Membership, Profile
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from .forms import ClassForm, SessionForm, PrivateClassRequestForm  
import copy
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Q

# Define the group checks
def is_ceo_or_boss(user):
    return user.groups.filter(name='CEO and Boss').exists()

def is_team_member(user):
    return user.groups.filter(name='Team Members').exists()

def is_trainer(user):
    return user.groups.filter(name='Trainers').exists()

def is_ceo_boss_or_team_member(user):
    return is_ceo_or_boss(user) or is_team_member(user)

def get_week_range(week_offset):
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())  # Monday of this week
    start_week = start_of_week + timedelta(weeks=week_offset)  # Monday of target week
    end_week = start_week + timedelta(days=6)  # Sunday of target week
    return start_week, end_week

def class_list(request):
    try:
        week_offset = int(request.GET.get('week', 0))
    except ValueError:
        return HttpResponseBadRequest(_("Invalid week parameter"))

    start_week, end_week = get_week_range(week_offset)
    sessions = Session.objects.filter(start_time__date__lte=end_week, end_time__date__gte=start_week).select_related('class_meta').order_by('start_time')

    filtered_sessions = []
    for session in sessions:
        if session.recurring and session.recurrence_end_date:
            days_since_start = (start_week - session.start_time.date()).days
            days_until_start = days_since_start % 7
            first_occurrence = start_week + timedelta(days=(7 - days_until_start)) if days_until_start > 0 else start_week

            current_start_date = first_occurrence
            while current_start_date <= min(session.recurrence_end_date, end_week):
                session_copy = copy.copy(session)
                session_copy.start_time = session.start_time + timedelta(days=(current_start_date - session.start_time.date()).days)
                session_copy.end_time = session.end_time + timedelta(days=(current_start_date - session.start_time.date()).days)
                filtered_sessions.append(session_copy)
                current_start_date += timedelta(weeks=1)
        elif start_week <= session.start_time.date() <= end_week:
            filtered_sessions.append(session)

    sessions_by_day = {start_week + timedelta(days=i): [] for i in range(7)}
    for session in filtered_sessions:
        sessions_by_day[session.start_time.date()].append(session)

    context = {
        'sessions_by_day': sessions_by_day,
        'previous_week': week_offset - 1,
        'next_week': week_offset + 1,
        'start_week': start_week,
        'end_week': end_week
    }
    return render(request, 'class_schedule/class_list.html', context)

def class_detail(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    now = timezone.now()
    upcoming_sessions = class_obj.sessions.filter(start_time__gte=now).order_by('start_time')
    past_sessions = class_obj.sessions.filter(start_time__lt=now).order_by('-start_time')

    return render(request, 'class_schedule/class_detail.html', {
        'class': class_obj,
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
        'now': now
    })

def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    bookings = session.bookings.select_related('user')

    active_members = User.objects.filter(
        Q(membership__end_date__isnull=True) | Q(membership__end_date__gt=timezone.now().date()),
        membership__isnull=False
    ).select_related('membership').distinct()

    context = {
        'session': session,
        'bookings': bookings,
        'active_members': active_members,
    }
    return render(request, 'class_schedule/session_detail.html', context)

@login_required
@transaction.atomic
def book_class(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if session.bookings.filter(user=request.user).exists():
        messages.error(request, _('You have already booked this class.'))
    else:
        Booking.objects.create(session=session, user=request.user)
        messages.success(request, _('Class booked successfully.'))
    return redirect('class_detail', class_id=session.class_meta.id)

@login_required
def unbook_class(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.session.start_time <= timezone.now():
        messages.error(request, _('You cannot cancel bookings for past sessions.'))
    elif timezone.now() >= booking.session.start_time - timedelta(hours=24):
        messages.error(request, _('Bookings can only be canceled more than 24 hours in advance.'))
    else:
        booking.delete()
        messages.success(request, _('Your booking has been successfully canceled.'))
    return redirect('class_detail', class_id=booking.session.class_meta.id)

class InactiveMembershipError(Exception):
    pass

@login_required
def personal_schedule(request):
    try:
        profile = Profile.objects.get(user=request.user)
        membership = Membership.objects.get(user=request.user)
        if not membership.is_active():
            raise InactiveMembershipError(_('Membership is not active.'))
        qr_code_url = profile.qr_code.url if profile.qr_code else None
    except (Profile.DoesNotExist, Membership.DoesNotExist, InactiveMembershipError) as e:
        messages.error(request, str(e))
        return redirect('home')

    upcoming_bookings = Booking.objects.filter(
        user=request.user,
        session__start_time__gte=timezone.now()
    ).select_related('session', 'session__class_meta').order_by('session__start_time')

    return render(request, 'class_schedule/personal_schedule.html', {
        'upcoming_bookings': upcoming_bookings,
        'membership': membership,
        'qr_code_url': qr_code_url,
        'now': timezone.now()
    })

@user_passes_test(is_ceo_boss_or_team_member)
def handle_class_form(request, form_cls, success_message, template_name, redirect_url, instance=None):
    if request.method == 'POST':
        form = form_cls(request.POST, instance=instance)
        if form.is_valid():
            new_class = form.save()
            messages.success(request, _(success_message))
            return redirect(redirect_url, class_id=new_class.id)
    else:
        form = form_cls(instance=instance)
    return render(request, template_name, {'form': form})

@user_passes_test(is_ceo_boss_or_team_member)
def add_class(request):
    return handle_class_form(
        request,
        ClassForm,
        _('New class added successfully.'),
        'class_schedule/add_class.html',
        'class_detail'
    )

@user_passes_test(is_ceo_boss_or_team_member)
def remove_class(request, class_id):
    if request.method == 'POST':
        class_obj = get_object_or_404(Class, id=class_id)
        class_obj.delete()
        messages.success(request, _('Class removed successfully.'))
        return redirect('class_list')
    return render(request, 'class_schedule/remove_class.html', {'class_id': class_id})

@user_passes_test(is_ceo_boss_or_team_member)
def handle_session_form(request, class_id, form_cls, success_message, template_name, redirect_url, instance=None):
    class_obj = get_object_or_404(Class, id=class_id)
    if request.method == 'POST':
        form = form_cls(request.POST, instance=instance)
        if form.is_valid():
            new_session = form.save(commit=False)
            new_session.class_meta = class_obj
            new_session.save()
            messages.success(request, _(success_message))
            return redirect(redirect_url, class_id=class_id)
    else:
        form = form_cls(instance=instance)
    return render(request, template_name, {'form': form, 'class': class_obj})

@user_passes_test(is_ceo_boss_or_team_member)
def add_session(request, class_id):
    return handle_session_form(
        request,
        class_id,
        SessionForm,
        _('New session added successfully.'),
        'class_schedule/add_session.html',
        'class_detail'
    )

@user_passes_test(is_ceo_boss_or_team_member)
def remove_session(request, session_id):
    if request.method == 'POST':
        session = get_object_or_404(Session, id=session_id)
        class_id = session.class_meta.id
        session.delete()
        messages.success(request, _('Session removed successfully.'))
        return redirect('class_detail', class_id=class_id)
    return render(request, 'class_schedule/remove_session.html', {'session_id': session_id})

@user_passes_test(is_ceo_boss_or_team_member)
def remove_all_sessions(request, session_id):
    if request.method == 'POST':
        with transaction.atomic():
            session = get_object_or_404(Session, id=session_id)
            class_id = session.class_meta.id

            if session.recurring:
                Session.objects.filter(
                    class_meta_id=class_id,
                    start_time__gte=session.start_time,
                    start_time__lte=session.recurrence_end_date
                ).delete()
            else:
                session.delete()

            messages.success(request, _('Session removed successfully.'))
            return redirect('class_detail', class_id=class_id)
    return render(request, 'class_schedule/remove_session.html', {'session_id': session_id})

@login_required
@permission_required('class_schedule.add_booking', raise_exception=True)
@transaction.atomic
def add_member_to_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        if not session.bookings.filter(user=user).exists():
            Booking.objects.create(session=session, user=user)
            messages.success(request, _('%s added to session.') % user.username)
        else:
            messages.warning(request, _('%s is already in the session.') % user.username)
    return redirect('session_detail', session_id=session.id)

@login_required
@permission_required('class_schedule.delete_booking', raise_exception=True)
@transaction.atomic
def remove_member_from_session(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.method == 'POST':
        booking.delete()
        messages.success(request, _('Member removed from session successfully.'))
    return redirect('session_detail', session_id=booking.session.id)

@login_required
def request_private_class(request):
    if request.method == 'POST':
        form = PrivateClassRequestForm(request.POST)
        if form.is_valid():
            private_class_request = form.save(commit=False)
            private_class_request.user = request.user
            if not Membership.objects.filter(user=request.user, end_date__gt=timezone.now()).exists():
                messages.error(request, _('You must be a member to request a private class.'))
                return redirect('private_class_requests')
            private_class_request.save()
            messages.success(request, _('Your private class request has been submitted successfully.'))
            return redirect('private_class_requests')
        else:
            messages.error(request, _('There was an error with your submission. Please correct the errors below.'))
    else:
        form = PrivateClassRequestForm()

    context = {
        'form': form,
    }
    return render(request, 'class_schedule/request_private_class.html', context)

@login_required
def private_class_requests(request):
    requests = PrivateClassRequest.objects.filter(user=request.user).order_by('-requested_date')
    context = {
        'requests': requests,
    }
    return render(request, 'class_schedule/private_class_requests.html', context)

@login_required
@user_passes_test(lambda user: user.groups.filter(name__in=['CEO and Boss', 'Team Members']).exists())
def private_class_requests_list(request):
    requests = PrivateClassRequest.objects.filter(status='pending').select_related('user', 'trainer')
    return render(request, 'class_schedule/private_class_requests_list.html', {'requests': requests})

@login_required
@user_passes_test(lambda user: user.groups.filter(name__in=['CEO and Boss', 'Team Members']).exists())
def approve_private_class_request(request, request_id):
    private_class_request = get_object_or_404(PrivateClassRequest, id=request_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            private_class_request.status = 'approved'
            messages.success(request, _('Private class request from %s approved.') % private_class_request.user.username)
        elif action == 'deny':
            private_class_request.status = 'denied'
            messages.success(request, _('Private class request from %s denied.') % private_class_request.user.username)
        private_class_request.save()
    return redirect('private_class_requests_list')
