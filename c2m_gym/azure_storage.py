from django.conf import settings
from storages.backends.azure_storage import AzureStorage, BlobServiceClient

class AzureMediaStorage(AzureStorage):
    account_name = settings.AZURE_ACCOUNT_NAME
    account_key = settings.AZURE_STORAGE_KEY
    azure_container = settings.AZURE_MEDIA_CONTAINER
    expiration_secs = None
    overwrite_files = True

    connection_string = settings.AZURE_BLOB_CONNECTION_STRING

    def custom_service_client(self):
        return BlobServiceClient.from_connection_string(self.connection_string)