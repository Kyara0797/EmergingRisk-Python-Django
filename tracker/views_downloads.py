# tracker/views_downloads.py
import os, uuid
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.utils.encoding import smart_str
from django.db import transaction
from tracker.models import Source, SourceFileVersion, DownloadLog

def _resolve_object(tok: uuid.UUID):
    src = Source.objects.filter(download_token=tok).first()
    if src and src.file_upload:
        return src, src.file_upload, f"source:{src.pk}"
    sfv = SourceFileVersion.objects.filter(download_token=tok).first()
    if sfv and sfv.file:
        return sfv, sfv.file, f"sourcefileversion:{sfv.pk}"
    return None, None, None

@login_required
def secure_file_download(request, token):
    try:
        tok = token if isinstance(token, uuid.UUID) else uuid.UUID(str(token))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid token.")

    obj, filefield, object_key = _resolve_object(tok)
    if not obj or not filefield:
        raise Http404("File not found.")

    storage = default_storage
    path = filefield.name
    if not storage.exists(path):
        raise Http404("File missing on storage.")

    with transaction.atomic():
        DownloadLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            object_key=object_key,
            token=tok,
        )

    # Filesystem: local stream
    try:
        local_path = storage.path(path)
        filename = os.path.basename(local_path)
        return FileResponse(open(local_path, "rb"), as_attachment=True, filename=smart_str(filename))
    except NotImplementedError:
        # Para S3/Azure privado: aquí iría redirección a URL firmada.
        raise Http404("Storage not supported in this mode.")
