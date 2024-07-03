from modeltranslation.translator import translator, TranslationOptions
from .models import Class, Session, Booking

class ClassTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

class SessionTranslationOptions(TranslationOptions):
    fields = ()

class BookingTranslationOptions(TranslationOptions):
    fields = ()

translator.register(Class, ClassTranslationOptions)
translator.register(Session, SessionTranslationOptions)
translator.register(Booking, BookingTranslationOptions)