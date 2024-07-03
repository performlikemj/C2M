# gymApp/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Specific paths
    path('update_membership/<int:pk>/', views.update_membership, name='update_membership'),
    path('delete_membership/<int:pk>/', views.delete_membership, name='delete_membership'),
    path('edit_user/<int:pk>/', views.edit_user, name='edit_user'),
    path('delete_user/<int:pk>/', views.delete_user, name='delete_user'),

    # Explicit QR Code action paths
    path('check_in/<str:qr_code_data>/', views.process_qr_action, {'action': 'check_in'}, name='process_qr_action_check_in'),
    path('check_out/<str:qr_code_data>/', views.process_qr_action, {'action': 'check_out'}, name='process_qr_action_check_out'),

    # Authentication paths
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('scan/', views.scan, name='scan'),
    path('select_session/<str:scan_user>/', views.select_session_type, name='select_session_type'),

    # Membership paths
    path('manage_memberships/', views.manage_memberships, name='manage_memberships'),
    path('add_membership/', views.add_membership, name='add_membership'),
    path('select_membership/', views.select_membership, name='select_membership'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification-email/', views.resend_verification_email, name='resend_verification_email'),


    # User paths
    path('list_users/', views.list_users, name='list_users'),
    path('view_user_documents/<int:user_id>/', views.view_user_documents, name='view_user_documents'),
    path('verify_document/<int:submission_id>/', views.verify_document, name='verify_document'),
    path('add_user/', views.add_user, name='add_user'),
    path('edit_profile/', views.edit_own_profile, name='edit_own_profile'),

    # Stripe checkout paths
    path('payment/<int:membership_type_id>/', views.create_checkout_session, name='payment_page'),
    path('add-payment-method/', views.add_payment_method, name='add_payment_method'),
    # path('webhook/', views.stripe_webhook, name='stripe_webhook'),

    # Payment-related paths
    path('payment/checkout/<int:membership_type_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('payment/success/', views.payment_success, name='payment_success'),  # Ensure this path is correct
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),

]
