import os
from azure.storage.blob import BlobServiceClient
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Upload existing media files to Azure Blob Storage'

    def handle(self, *args, **kwargs):
        # Environment variables
        account_name = settings.AZURE_ACCOUNT_NAME
        account_key = settings.AZURE_STORAGE_KEY
        container_name = settings.AZURE_MEDIA_CONTAINER
        media_root = settings.MEDIA_ROOT

        # Connect to Azure Blob Storage
        blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
        container_client = blob_service_client.get_container_client(container_name)

        # Upload files to the Azure Blob container
        def upload_files(directory, container_client):
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    blob_path = os.path.relpath(file_path, media_root)
                    blob_client = container_client.get_blob_client(blob_path)
                    
                    self.stdout.write(f"Uploading {file_path} to {blob_path}...")
                    with open(file_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)
                    self.stdout.write(self.style.SUCCESS(f"Uploaded {file_path} to {blob_path}"))

        # Run the upload
        upload_files(media_root, container_client)
