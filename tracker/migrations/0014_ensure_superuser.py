# tracker/migrations/0014_ensure_superuser.py
from django.db import migrations

def ensure_superuser(apps, schema_editor):
    import os
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email    = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "root1234")  # usa el de tus Variables

    if not password:
        # No cortamos el deploy si falta; solo informamos.
        print("⚠️ DJANGO_SUPERUSER_PASSWORD no está definido; se omite.")
        return

    u, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_staff": True, "is_superuser": True},
    )
    # Asegurar privilegios y contraseña SIEMPRE
    u.is_staff = True
    u.is_superuser = True
    u.email = email
    u.set_password(password)
    u.save()
    print(("✅ Creado" if created else "✅ Actualizado") + f" superuser: {u.username}")

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0013_source_is_active"),  # <-- tu ÚLTIMA migración (según la captura)
    ]

    operations = [
        migrations.RunPython(ensure_superuser, reverse_code=noop),
    ]
