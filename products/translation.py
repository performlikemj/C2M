from modeltranslation.translator import translator, TranslationOptions
from .models import Product, Cart, CartItem

class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class CartTranslationOptions(TranslationOptions):
    fields = ()

class CartItemTranslationOptions(TranslationOptions):
    fields = ()

translator.register(Product, ProductTranslationOptions)
translator.register(Cart, CartTranslationOptions)
translator.register(CartItem, CartItemTranslationOptions)