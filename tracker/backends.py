# tracker/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Normaliza la entrada
        username = (username or "").strip()

        User = get_user_model()
        # Intentamos por email (case-insensitive)
        qs = User.objects.filter(Q(email__iexact=username))
        count = qs.count()
        if count == 1:
            user = qs.first()
        elif count > 1:
            # Email duplicado → No autenticar por email
            return None
        else:
            # Probar por username (case-insensitive)
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
