# gym_info/models.py 
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

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


    def save(self, *args, **kwargs):
        logger.debug(f"Saving trainer: {self.name}")
        if self.photo:
            logger.debug(f"Photo uploaded: {self.photo.name}")
        else:
            logger.debug("No photo uploaded")
        super().save(*args, **kwargs)

class ContactInfo(models.Model):
    instagram_url = models.URLField(blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Contact Information"
