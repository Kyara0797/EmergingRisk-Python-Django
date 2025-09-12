# tracker/views_downloads.py
import os
import uuid
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.utils.encoding import smart_str
from django.db import transaction

from tracker.models import Source, SourceFileVersion, DownloadLog

def _resolve_object(token: uuid.UUID):
    obj = Source.objects.filter(download_token=token).first()
    if obj:
        filefield = obj.file_upload
        object_key = f"source:{obj.pk}"
        return obj, filefield, object_key

    fv = SourceFileVersion.objects.filter(download_token=token).first()
    if fv:
        filefield = fv.file
        object_key = f"sourcefileversion:{fv.pk}"
        return fv, filefield, object_key

    return None, None, None

@login_required
def secure_file_download(request, token):
    # token ya viene validado por el path converter <uuid:token>
    if not isinstance(token, uuid.UUID):
        return HttpResponseBadRequest("Invalid token.")

    obj, filefield, object_key = _resolve_object(token)
    if not obj or not filefield:
        raise Http404("File not found.")

    storage = default_storage
    path = filefield.name
    if not storage.exists(path):
        raise Http404("File missing on storage.")

    # Logeamos el intento
    with transaction.atomic():
        DownloadLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            object_key=object_key,
            token=token,
        )

    # Filesystem (Render) → stream local
    try:
        local_path = storage.path(path)  # FileSystemStorage lo soporta
        filename = os.path.basename(local_path)
        resp = FileResponse(open(local_path, "rb"), as_attachment=True, filename=smart_str(filename))
        return resp
    except NotImplementedError:
        # Para S3/Azure públicos podrías redirigir a URL firmada aquí si lo cambias en el futuro
        raise Http404("Storage not supported in this mode.")
