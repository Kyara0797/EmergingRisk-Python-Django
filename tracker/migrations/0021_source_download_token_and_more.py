# tracker/migrations/0021_source_download_token_and_more.py
# Ajustado para evitar el UNIQUE en SQLite durante la migración inicial.
from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings


def backfill_tokens(apps, schema_editor):
    Source = apps.get_model('tracker', 'Source')
    SourceFileVersion = apps.get_model('tracker', 'SourceFileVersion')

    for Model in (Source, SourceFileVersion):
        qs = Model.objects.filter(download_token__isnull=True)
        for obj in qs.iterator():
            tok = uuid.uuid4()
            # Colisión es muy improbable; por robustez revisamos.
            while Model.objects.filter(download_token=tok).exists():
                tok = uuid.uuid4()
            obj.download_token = tok
            obj.save(update_fields=['download_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0020_tempupload'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1) Añadir campos como NULL y sin unique/default (preparación)
        migrations.AddField(
            model_name='source',
            name='download_token',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name='sourcefileversion',
            name='download_token',
            field=models.UUIDField(null=True, editable=False),
        ),

        # Mantener los cambios que ya traías en 0021:
        migrations.AlterField(
            model_name='source',
            name='potential_impact',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=20,
                choices=[
                    ('ESCALATING', 'Escalating'),
                    ('DECREASING', 'Decreasing'),
                    ('MAINTAINING', 'Maintaining'),
                ],
            ),
        ),
        migrations.CreateModel(
            name='DownloadLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('when', models.DateTimeField(auto_now_add=True)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, default='')),
                ('object_key', models.TextField()),
                ('token', models.UUIDField()),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-when'],
                'indexes': [
                    models.Index(fields=['-when'], name='tracker_dow_when_340c73_idx'),
                    models.Index(fields=['token'], name='tracker_dow_token_db57e7_idx'),
                ],
            },
        ),

        # 2) Backfill de tokens para filas existentes
        migrations.RunPython(backfill_tokens, migrations.RunPython.noop),

        # 3) Finalizar: unique + NOT NULL + default callable
        migrations.AlterField(
            model_name='source',
            name='download_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, null=False, editable=False),
        ),
        migrations.AlterField(
            model_name='sourcefileversion',
            name='download_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, null=False, editable=False),
        ),
    ]
