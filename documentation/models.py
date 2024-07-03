# documentation/models.py
from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='documents/')

    def __str__(self):
        return self.name

class UserDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    submission = models.FileField(upload_to='submissions/')
    submitted = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.document.name} - {'Verified' if self.verified else 'Pending Verification'}"
