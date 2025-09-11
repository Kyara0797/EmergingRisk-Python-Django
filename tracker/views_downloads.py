# tracker/views_downloads.py
import uuid
import mimetypes
from django.http import FileResponse, Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.encoding import smart_str

from .models import Source, SourceFileVersion, DownloadLog


def _find_object_by_token(tok: uuid.UUID):
    """Devuelve (obj, filefield, object_key) para el token dado."""
    src = Source.objects.filter(download_token=tok).first()
    if src and src.file_upload:
        return src, src.file_upload, f"Source:{src.id}"

    ver = SourceFileVersion.objects.filter(download_token=tok).first()
    if ver and ver.file:
        return ver, ver.file, f"SourceFileVersion:{ver.id}"

    return None, None, None


def secure_file_download(request, token):
    """
    Descarga segura por token UUID:
      - Busca token en Source/SourceFileVersion.
      - Si storage es S3/Azure (o público), redirige a URL (posible firmada).
      - Si filesystem, hace streaming con FileResponse.
      - Registra DownloadLog (best-effort).
    """
    # Acepta token como str o uuid.UUID
    try:
        tok = uuid.UUID(str(token))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid token")

    obj, filefield, object_key = _find_object_by_token(tok)
    if not filefield:
        raise Http404("File not found for this token")

    # Log best-effort
    try:
        DownloadLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            object_key=object_key,
            token=tok,
        )
    except Exception:
        pass

    # Intento 1: si el storage provee URL pública/firmada útil, redirigimos
    backend = settings.STORAGES["default"]["BACKEND"]
    try:
        url = filefield.storage.url(filefield.name)
        # Para FileSystemStorage .url() devuelve /media/... (normalmente NO servido en prod).
        # Para S3/Azure privado, nuestras storages suelen devolver URL firmada: redirigimos.
        if backend != "django.core.files.storage.FileSystemStorage":
            return HttpResponseRedirect(url)
    except Exception:
        # Si falla, caemos a streaming
        pass

    # Intento 2 (filesystem o fallback): streaming del archivo
    try:
        fh = filefield.open("rb")
    except Exception:
        raise Http404("File not found on storage")

    filename = filefield.name.split("/")[-1]
    content_type, _ = mimetypes.guess_type(filename)
    resp = FileResponse(fh, content_type=content_type or "application/octet-stream")
    # Content-Length y descarga sugerida
    try:
        resp["Content-Length"] = filefield.size
    except Exception:
        pass
    resp["Content-Disposition"] = f'attachment; filename="{smart_str(filename)}"'
    return resp
