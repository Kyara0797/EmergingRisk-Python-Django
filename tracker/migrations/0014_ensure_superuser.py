from django.db import migrations
import os

def ensure_superuser(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email    = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

    if not password:
        print("⚠️ DJANGO_SUPERUSER_PASSWORD no definido; se omite.")
        return

    u, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_staff": True, "is_superuser": True},
    )
    u.is_staff = True
    u.is_superuser = True
    u.email = email
    u.set_password(password)
    u.save()
    print(("✅ Creado" if created else "✅ Actualizado") + f" superuser: {u.username}")

class Migration(migrations.Migration):
    dependencies = [
        # ¡Importante! Deja la dependencia que tu archivo generó automáticamente
        # (apunta a la última migración real de 'tracker'). No cambies esto.
        # Ejemplo generado: ("tracker", "0013_lo_que_sea")
    ]
    operations = [migrations.RunPython(ensure_superuser)]
