# tracker/migrations/0002_create_superuser.py
from django.db import migrations

def create_or_update_superuser(apps, schema_editor):
    import os
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email    = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")  # requerido

    if not password:
        print("⚠️ DJANGO_SUPERUSER_PASSWORD no está definido; se omite.")
        return

    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_staff": True, "is_superuser": True},
    )
    user.is_staff = True
    user.is_superuser = True
    user.email = email
    user.set_password(password)
    user.save()
    print(("✅ Creado" if created else "✅ Actualizado") + f" superuser: {user.username}")

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0001_initial"),  # <- ajusta si tu primera migración tiene otro nombre
    ]

    operations = [
        migrations.RunPython(create_or_update_superuser, reverse_code=noop),
    ]
