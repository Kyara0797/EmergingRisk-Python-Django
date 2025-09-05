# tracker/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Permite login con email o username (case-insensitive).
    No cambia el modelo; es totalmente compatible con el User estándar.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        User = get_user_model()
        # Intentamos por email primero
        qs = User.objects.filter(Q(email__iexact=username))
        count = qs.count()
        if count == 1:
            user = qs.first()
        elif count > 1:
            # Email duplicado -> no autenticar por email para no ambiguar
            return None
        else:
            # No hubo match por email: probamos por username
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
