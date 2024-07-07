# gym_info/models.py 
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
# from storages.backends.azure_storage import AzureStorage

# class AzureMediaStorage(AzureStorage):
#     account_name = settings.AZURE_ACCOUNT_NAME
#     account_key = settings.AZURE_STORAGE_KEY
#     azure_container = settings.AZURE_MEDIA_CONTAINER
#     expiration_secs = None
#     overwrite_files = True


# class AzureStaticStorage(AzureStorage):
#     account_name = settings.AZURE_ACCOUNT_NAME
#     account_key = settings.AZURE_STORAGE_KEY
#     azure_container = settings.AZURE_STATIC_CONTAINER
#     expiration_secs = None

# Updated Trainer model to link with User
class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile', null=True, blank=True)
    name = models.CharField(max_length=100)
    bio = models.TextField()
    photo = models.ImageField(upload_to='trainers/')

    def __str__(self):
        return f"{self.name}"

    def is_available(self, start_time, end_time, exclude_session_id=None):
        from gymApp.models import PersonalTrainingSession
        sessions = self.sessions.exclude(id=exclude_session_id) if exclude_session_id else self.sessions

        # Check for overlapping class sessions
        class_conflicts = sessions.filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        ).exists()

        if class_conflicts:
            return False

        # Check for overlapping personal training sessions
        personal_training_conflicts = PersonalTrainingSession.objects.filter(
            trainer=self,
            session__start_time__lt=end_time,
            session__end_time__gt=start_time
        ).exists()

        return not personal_training_conflicts


class ContactInfo(models.Model):
    instagram_url = models.URLField(blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Contact Information"
