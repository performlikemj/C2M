from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Trainer, ContactInfo
from .forms import TrainerForm, ContactInfoForm
from django.contrib import messages

def home(request):
    services = {
        'Muay Thai': {
            'description': _('Learn the art of eight limbs.'),
            'image': 'images/muay_thai.jpg'
        },
        'Boxing': {
            'description': _('The classic discipline of striking and defense.'),
            'image': 'images/boxing.jpg'
        },
        'Personal Training': {
            'description': _('Tailored fitness programs for your goals.'),
            'image': 'images/personal_training.jpg'
        },
        'Guest Training': {
            'description': _('Train with the best guest trainers in the world.'),
            'image': 'images/guest_training.jpg'
        },
        'Massage Therapy': {
            'description': _('Rejuvenate with professional massage treatments.'),
            'image': 'images/massage_therapy.jpg'
        },
        'Dietician': {
            'description': _('Nutritional plans for optimal performance.'),
            'image': 'images/dietician.jpg'
        }
    }

    return render(request, 'gym_info/home.html', {'now': timezone.now(), 'services': services})

def trainers(request):
    trainer_list = Trainer.objects.all()
    context = {'trainers': trainer_list, 'now': timezone.now()}
    return render(request, 'gym_info/trainers.html', context)

def trainer_detail(request, trainer_id):
    trainer = Trainer.objects.get(id=trainer_id)
    context = {'trainer': trainer, 'now': timezone.now()}
    return render(request, 'gym_info/trainer_detail.html', context)

def is_ceo_or_boss(user):
    return user.groups.filter(name='CEO and Boss').exists()

def is_team_member(user):
    return user.groups.filter(name='Team Members').exists()

def is_trainer(user):
    return user.groups.filter(name='Trainers').exists()

def is_ceo_boss_or_team_member(user):
    return is_ceo_or_boss(user) or is_team_member(user)

@login_required
@user_passes_test(is_ceo_boss_or_team_member)
def edit_trainer(request, trainer_id):
    trainer = get_object_or_404(Trainer, id=trainer_id)
    if request.method == 'POST':
        form = TrainerForm(request.POST, instance=trainer)
        if form.is_valid():
            form.save()
            messages.success(request, _('Trainer updated successfully.'))
            return redirect('trainers')
        else:
            messages.error(request, _('Please correct the error below.'))
    else:
        form = TrainerForm(instance=trainer)
    context = {'form': form, 'trainer': trainer, 'now': timezone.now()}
    return render(request, 'gym_info/edit_trainer.html', context)

@login_required
@user_passes_test(is_ceo_boss_or_team_member)
def delete_trainer(request, trainer_id):
    trainer = get_object_or_404(Trainer, id=trainer_id)
    if request.method == 'POST':
        trainer.delete()
        messages.success(request, _('Trainer deleted successfully.'))
        return redirect(reverse('trainers'))
    return render(request, 'gym_info/delete_trainer.html', {'trainer': trainer, 'now': timezone.now()})

@login_required
@user_passes_test(is_ceo_boss_or_team_member)
def new_trainer(request):
    if request.method == 'POST':
        form = TrainerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('New trainer added successfully.'))
            return redirect('trainers')
        else:
            messages.error(request, _('Please correct the error below.'))
    else:
        form = TrainerForm()
    return render(request, 'gym_info/new_trainer.html', {'form': form, 'now': timezone.now()})

@login_required
@user_passes_test(is_ceo_boss_or_team_member)
def manage_contact_info(request):
    contact_info, created = ContactInfo.objects.get_or_create(pk=1)
    if request.method == 'POST':
        form = ContactInfoForm(request.POST, instance=contact_info)
        if form.is_valid():
            form.save()
            messages.success(request, _('Contact information updated successfully.'))
            return redirect('contact_info')
        else:
            messages.error(request, _('Please correct the error below.'))
    else:
        form = ContactInfoForm(instance=contact_info)
    return render(request, 'gym_info/manage_contact_info.html', {'form': form, 'now': timezone.now()})

def contact_info(request):
    try:
        contact_info = ContactInfo.objects.get(pk=1)
    except ContactInfo.DoesNotExist:
        contact_info = None
    
    return render(request, 'gym_info/contact_info.html', {
        'contact_info': contact_info,
        'now': timezone.now()
    })
