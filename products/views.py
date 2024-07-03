# products/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext as _  # Import the translation function
from .models import Product, Cart, CartItem
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import stripe

@login_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('view_cart')

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    if created:
        # Adding a message for when a new cart is created
        messages.info(request, _('A new cart has been created for you.'))
    return render(request, 'products/cart.html', {'cart': cart})

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        messages.success(request, _('Item quantity reduced by one.'))
    else:
        item.delete()
        messages.success(request, _('Item removed from cart.'))
    return redirect('view_cart')

@login_required
def create_checkout_session(request):
    cart = get_object_or_404(Cart, user=request.user)
    line_items = [{
        'price_data': {
            'currency': 'jpy',
            'product_data': {
                'name': item.product.name,
            },
            'unit_amount': int(item.product.price * 100),
        },
        'quantity': item.quantity,
    } for item in cart.items.all()]

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri('/') + '?success=true',
        cancel_url=request.build_absolute_uri('/') + '?canceled=true',
    )
    messages.info(request, _('You are being redirected to the payment gateway.'))
    return redirect(checkout_session.url)
