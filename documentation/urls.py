# documentation/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('documents/', views.list_documents, name='list_documents'),
    path('documents/submit/<int:document_id>/', views.submit_document, name='submit_document'),
]
