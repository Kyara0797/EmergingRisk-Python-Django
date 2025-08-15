import logging
from django.db.models.signals import pre_save, post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from .models import Theme, UserAccessLog
from ipware import get_client_ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    client_ip, is_routable = get_client_ip(request)
    UserAccessLog.objects.create(
        user=user,
        ip_address=client_ip,
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

from django.contrib.auth.signals import user_logged_out

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:  # Asegurarse que el usuario está autenticado
        last_login = UserAccessLog.objects.filter(user=user).last()
        if last_login:
            last_login.logout_time = timezone.now()
            last_login.save()

logger = logging.getLogger(__name__)
@receiver(pre_save, sender=Theme)
def log_theme_changes(sender, instance, **kwargs):
    """
    Save changes to Theme models before saving
    """
    if instance.pk:  
        try:
            old = Theme.objects.get(pk=instance.pk)
            changes = {}
            
            for field in instance._meta.fields:
                old_val = getattr(old, field.name)
                new_val = getattr(instance, field.name)
                if old_val != new_val:
                    changes[field.name] = (old_val, new_val)
            
            if changes:
                logger.info(f"Changes detected in Theme ID {instance.pk}: {changes}")
                
        except Theme.DoesNotExist:
            logger.warning(f"Attempt to update non-existent theme (ID: {instance.pk})")