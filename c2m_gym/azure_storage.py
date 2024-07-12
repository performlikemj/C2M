from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from azure.storage.blob import BlobServiceClient

class AzureMediaStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_STORAGE_KEY
    azure_container = settings.AZURE_MEDIA_CONTAINER
    expiration_secs = None
    overwrite_files = True

    connection_string = settings.AZURE_BLOB_CONNECTION_STRING

    def __init__(self, *args, **kwargs):
        if not self.connection_string:
            raise ValueError("AZURE_CONNECTION_STRING must be set.")
        self.custom_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        super().__init__(*args, **kwargs)

    def custom_service_client(self):
        return BlobServiceClient.from_connection_string(self.connection_string)