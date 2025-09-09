# tracker/views_downloads.py
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.core.files.storage import default_storage
from ipware import get_client_ip

from .models import Source, SourceFileVersion, DownloadLog

def _user_can_access_source(user, source: Source) -> bool:
    """
    Regla mínima: debe estar autenticado.
    Endurézalo si quieres: staff, pertenencia a área, rol, etc.
    """
    return user.is_authenticated

@login_required
def secure_file_download(request, token):
    """
    Enlace estable: /f/<token>/ -> audita -> redirige a URL del storage (privado => firmada).
    - Si el token pertenece a una versión histórica, sirve esa.
    - Si pertenece al Source “actual”:
        * si hay file_upload -> sirve ese archivo
        * si sólo hay link_or_file -> audita y redirige al link externo
    """
    # 1) ¿Es una versión histórica?
    version = SourceFileVersion.objects.select_related("source").filter(download_token=token).first()
    if version:
        if not _user_can_access_source(request.user, version.source):
            return HttpResponseForbidden("Not allowed")

        object_key = version.file.name
        ip, _ = get_client_ip(request)
        DownloadLog.objects.create(
            user=request.user,
            ip=ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            object_key=object_key,
            token=version.download_token,
        )
        # Para S3/Azure privados, esta URL vendrá firmada automáticamente
        return redirect(default_storage.url(object_key))

    # 2) ¿Es el Source “actual”?
    src = Source.objects.filter(download_token=token).first()
    if not src:
        raise Http404("Invalid token")

    if not _user_can_access_source(request.user, src):
        return HttpResponseForbidden("Not allowed")

    # Determina a qué redirigir
    if src.file_upload:
        object_key = src.file_upload.name
        url = default_storage.url(object_key)
    elif src.link_or_file:
        object_key = src.link_or_file
        url = src.link_or_file
    else:
        raise Http404("No file or link attached to this source")

    ip, _ = get_client_ip(request)
    DownloadLog.objects.create(
        user=request.user,
        ip=ip,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        object_key=object_key,
        token=src.download_token,
    )
    return redirect(url)
