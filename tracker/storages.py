# tracker/storages.py
import os

MEDIA_PROVIDER = os.getenv("MEDIA_PROVIDER", "filesystem").lower()

# imports tolerantes + stubs (evita “Unresolved import” en el IDE)
try:
    from storages.backends.s3boto3 import S3Boto3Storage as _S3Base  # type: ignore
    _HAS_S3 = True
except Exception:  # pragma: no cover
    _HAS_S3 = False
    class _S3Base:  # stub
        pass

try:
    from storages.backends.azure_storage import AzureStorage as _AzureBase  # type: ignore
    _HAS_AZURE = True
except Exception:  # pragma: no cover
    _HAS_AZURE = False
    class _AzureBase:  # stub
        pass


if MEDIA_PROVIDER == "s3":
    if not _HAS_S3:
        raise ImportError(
            "Falta 'django-storages[boto3]' y/o 'boto3'. "
            "Instala: pip install 'django-storages[boto3]>=1.14.3' boto3"
        )

    class S3PrivateMediaStorage(_S3Base):
        default_acl       = "private"
        file_overwrite    = False
        custom_domain     = None
        querystring_auth  = True
        object_parameters = {"CacheControl": "max-age=60, s-maxage=60"}

    class S3PublicMediaStorage(_S3Base):
        default_acl       = "public-read"
        file_overwrite    = False
        querystring_auth  = False
        object_parameters = {"CacheControl": "public, max-age=31536000, immutable"}

elif MEDIA_PROVIDER == "azure":
    if not _HAS_AZURE:
        raise ImportError(
            "Falta 'django-storages[azure]' y/o 'azure-storage-blob'. "
            "Instala: pip install 'django-storages[azure]>=1.14.3' azure-storage-blob"
        )

    class AzurePrivateMediaStorage(_AzureBase):
        account_name    = os.getenv("AZURE_ACCOUNT_NAME")
        account_key     = os.getenv("AZURE_ACCOUNT_KEY")
        azure_container = os.getenv("AZURE_MEDIA_CONTAINER", "media")
        expiration_secs = int(os.getenv("AZURE_URL_EXPIRATION_SECS", "300"))
        file_overwrite  = False
        cache_control   = "max-age=60, s-maxage=60"

    class AzurePublicMediaStorage(_AzureBase):
        account_name    = os.getenv("AZURE_ACCOUNT_NAME")
        account_key     = os.getenv("AZURE_ACCOUNT_KEY")
        azure_container = os.getenv("AZURE_PUBLIC_CONTAINER", "media-public")
        expiration_secs = None
        file_overwrite  = False
        cache_control   = "public, max-age=31536000, immutable"

