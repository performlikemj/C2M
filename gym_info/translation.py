from modeltranslation.translator import translator, TranslationOptions
from .models import Trainer, ContactInfo

class TrainerTranslationOptions(TranslationOptions):
    fields = ('name', 'bio')

class ContactInfoTranslationOptions(TranslationOptions):
    fields = ()

translator.register(Trainer, TrainerTranslationOptions)
translator.register(ContactInfo, ContactInfoTranslationOptions)