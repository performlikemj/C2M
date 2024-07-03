# documentation/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Document, UserDocument
from .forms import UserDocumentForm

@login_required
def list_documents(request):
    documents = Document.objects.all()
    submissions = UserDocument.objects.filter(user=request.user)
    return render(request, 'documentation/list_documents.html', {
        'documents': documents,
        'submissions': submissions
    })

@login_required
def submit_document(request, document_id):
    document = get_object_or_404(Document, pk=document_id)
    if request.method == 'POST':
        form = UserDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            user_document = form.save(commit=False)
            user_document.user = request.user
            user_document.document = document
            user_document.save()
            return redirect('list_documents')
    else:
        form = UserDocumentForm()
    return render(request, 'documentation/submit_document.html', {'document': document, 'form': form})