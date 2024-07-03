from modeltranslation.translator import translator, TranslationOptions
from .models import Document, UserDocument

class DocumentTranslationOptions(TranslationOptions):
    fields = ('name',)

class UserDocumentTranslationOptions(TranslationOptions):
    fields = ()

translator.register(Document, DocumentTranslationOptions)
translator.register(UserDocument, UserDocumentTranslationOptions)