# class_schedule/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.class_list, name='class_list'),
    path('<int:class_id>/', views.class_detail, name='class_detail'),
    path('session_detail/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/add-member/', views.add_member_to_session, name='add_member_to_session'),
    path('book/<int:booking_id>/remove-member/', views.remove_member_from_session, name='remove_member_from_session'),
    path('book/<int:session_id>/', views.book_class, name='book_class'),
    path('unbook/<int:booking_id>/', views.unbook_class, name='unbook_class'),
    path('my_schedule/', views.personal_schedule, name='personal_schedule'),
    path('add_class/', views.add_class, name='add_class'),
    path('remove_class/<int:class_id>/', views.remove_class, name='remove_class'),
    path('add_session/<int:class_id>/', views.add_session, name='add_session'),
    path('remove_session/<int:session_id>/', views.remove_session, name='remove_session'),
    path('remove_all_sessions/<int:session_id>/', views.remove_all_sessions, name='remove_all_sessions'),\
    path('request_private_class/', views.request_private_class, name='request_private_class'),
    path('private_class_requests/', views.private_class_requests, name='private_class_requests'),
    path('private_class_requests_list/', views.private_class_requests_list, name='private_class_requests_list'),
    path('approve_private_class_request/<int:request_id>/', views.approve_private_class_request, name='approve_private_class_request'),
]
