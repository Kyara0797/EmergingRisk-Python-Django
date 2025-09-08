# tracker/storages.py
import os

# ===== Azure Blob =====
from storages.backends.azure_storage import AzureStorage

class AzurePrivateMediaStorage(AzureStorage):
    account_name   = os.getenv("AZURE_ACCOUNT_NAME")
    account_key    = os.getenv("AZURE_ACCOUNT_KEY")
    azure_container = os.getenv("AZURE_MEDIA_CONTAINER", "media")
    expiration_secs = int(os.getenv("AZURE_URL_EXPIRATION_SECS", "300"))  # SAS
    file_overwrite = False
    cache_control  = "max-age=60, s-maxage=60"
    # Contenedor privado (no public=True). .url será firmada.

class AzurePublicMediaStorage(AzureStorage):
    account_name   = os.getenv("AZURE_ACCOUNT_NAME")
    account_key    = os.getenv("AZURE_ACCOUNT_KEY")
    azure_container = os.getenv("AZURE_PUBLIC_CONTAINER", "media-public")
    expiration_secs = None  # sin SAS
    file_overwrite = False
    cache_control  = "public, max-age=31536000, immutable"
    # Debes dar "Access level: Blob" al contenedor en Portal para lectura pública.

# ===== S3 / compatibles =====
try:
    from storages.backends.s3boto3 import S3Boto3Storage
except Exception:  # pragma: no cover
    S3Boto3Storage = object  # evita fallo si no está instalado en algún entorno

class S3PrivateMediaStorage(S3Boto3Storage):
    default_acl      = "private"
    file_overwrite   = False
    custom_domain    = None         # usa endpoint por defecto (o define AWS_S3_CUSTOM_DOMAIN)
    querystring_auth = True         # URL firmada
    object_parameters = {"CacheControl": "max-age=60, s-maxage=60"}

class S3PublicMediaStorage(S3Boto3Storage):
    default_acl      = "public-read"
    file_overwrite   = False
    querystring_auth = False
    object_parameters = {"CacheControl": "public, max-age=31536000, immutable"}
