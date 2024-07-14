# gym_info/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('trainers/', views.trainers, name='trainers'),
    path('trainers/<int:trainer_id>/', views.trainer_detail, name='trainer_detail'),
    path('trainers/<int:trainer_id>/edit/', views.edit_trainer, name='edit_trainer'),
    path('trainers/<int:trainer_id>/delete/', views.delete_trainer, name='delete_trainer'),
    path('trainers/new/', views.new_trainer, name='new_trainer'),
    path('contact/', views.contact_info, name='contact_info'),
    path('contact/manage', views.manage_contact_info, name='manage_contact_info'),
    path('commerce-disclosure/', views.commerce_disclosure, name='commerce_disclosure'),
]