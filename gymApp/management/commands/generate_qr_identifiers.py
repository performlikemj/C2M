from django.core.management.base import BaseCommand
from gymApp.models import Profile

class Command(BaseCommand):
    help = 'Generates QR identifiers and QR codes for all profiles'

    def handle(self, *args, **options):
        profiles = Profile.objects.all()

        for profile in profiles:
            profile.qr_identifier = profile.generate_qr_identifier()
            profile.generate_qr_code()  # Generate QR code for the profile
            profile.save()

        self.stdout.write(self.style.SUCCESS('Successfully generated QR identifiers and QR codes for all profiles'))