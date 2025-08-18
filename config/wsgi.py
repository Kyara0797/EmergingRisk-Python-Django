import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# ====== DEBUG & FIX SUPERUSER (temporal, controlado por env) ======
if os.getenv("FORCE_SUPERUSER_ON_BOOT", "0") == "1":
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model

        User = get_user_model()
        # Print diagnóstico: cuántos usuarios hay y sus usernames
        total = User.objects.count()
        print(f"🔎 Usuarios en la BD: {total}")
        if total:
            print("🔎 Usernames:", list(User.objects.values_list('username', flat=True)[:10]))

        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email    = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not password:
            print("⚠️ DJANGO_SUPERUSER_PASSWORD no está definido; no se modifica superuser.")
        else:
            u, created = User.objects.get_or_create(username=username, defaults={"email": email})
            u.is_staff = True
            u.is_superuser = True
            u.email = email
            u.set_password(password)
            u.save()
            print(("✅ Creado" if created else "✅ Actualizado") + f" superuser: {u.username}")
    except Exception as e:
        print("⚠️ Error en FIX SUPERUSER:", e)
# ====== FIN BLOQUE TEMPORAL ======

application = get_wsgi_application()
