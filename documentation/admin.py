from django.contrib import admin
from .models import Document, UserDocument

class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name']

class UserDocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'document', 'submitted', 'verified']

admin.site.register(Document, DocumentAdmin)
admin.site.register(UserDocument, UserDocumentAdmin)

