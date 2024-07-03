# products/urls.py

from django.urls import path
from .views import product_list, add_to_cart, view_cart, remove_from_cart, create_checkout_session

urlpatterns = [
    path('', product_list, name='product_list'),
    path('add_to_cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', view_cart, name='view_cart'),
    path('remove_from_cart/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('checkout/', create_checkout_session, name='create_checkout_session'),
]
