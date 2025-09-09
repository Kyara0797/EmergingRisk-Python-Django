# tracker/management/commands/dedupe_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction, connection, IntegrityError
from django.utils import timezone
from django.db.utils import OperationalError, ProgrammingError


class Command(BaseCommand):
    help = (
        "Deduplica usuarios por email (case-insensitive): normaliza emails, "
        "conserva 1 por email (prioriza superuser, luego más reciente), "
        "reasigna FKs/M2M y crea índice único para prevenir futuros duplicados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Aplica los cambios. Sin esta bandera hace dry-run (muestra qué haría).",
        )
        parser.add_argument(
            "--keep-policy",
            choices=["superuser-first", "most-recent"],
            default="superuser-first",
            help="Criterio de conservación: superuser primero (default) o simplemente el más reciente.",
        )

    def handle(self, *args, **opts):
        commit = opts["commit"]
        keep_policy = opts["keep_policy"]
        vendor = connection.vendor
        User = get_user_model()

        # 1) Normalizar emails
        self.stdout.write(self.style.MIGRATE_HEADING("==> Normalizando emails (trim + lower; vacíos → NULL)"))
        changed = 0
        for u in User.objects.all().only("id", "email").iterator():
            orig = u.email
            if orig is None:
                continue
            e = (orig or "").strip()
            if not e:
                if commit:
                    User.objects.filter(pk=u.pk).update(email=None)
                changed += 1
            else:
                low = e.lower()
                if low != orig:
                    if commit:
                        User.objects.filter(pk=u.pk).update(email=low)
                    changed += 1
        self.stdout.write(f"Emails normalizados/ajustados: {changed}")

        # 2) Buscar duplicados por email (no NULL)
        self.stdout.write(self.style.MIGRATE_HEADING("==> Buscando duplicados por email (case-insensitive)"))
        users = list(
            User.objects.exclude(email__isnull=True).only("id", "email", "is_superuser", "date_joined")
        )
        by_email = {}
        for u in users:
            by_email.setdefault((u.email or "").lower(), []).append(u)

        dup_groups = {k: v for k, v in by_email.items() if len(v) > 1}
        if not dup_groups:
            self.stdout.write(self.style.SUCCESS("No hay duplicados."))
            self._ensure_unique_index(vendor)
            return

        self.stdout.write(self.style.WARNING(f"Encontrados {len(dup_groups)} email(es) con duplicados."))
        for email, lst in dup_groups.items():
            keeper = self._choose_keeper(lst, keep_policy)
            losers = [u.id for u in lst if u.id != keeper.id]
            self.stdout.write(f"  Email '{email}': conservando id={keeper.id}, eliminando {losers}")

        # Si es dry-run y hay duplicados, no intentes crear índice (evita el error de UNIQUE)
        if not commit:
            self.stdout.write(self.style.WARNING("Dry-run: no se aplicaron cambios ni se crea índice."))
            return

        # 3) Deduplicar + reasignar + DELETE crudo (sin parámetros)
        with transaction.atomic():
            for email, lst in dup_groups.items():
                keeper = self._choose_keeper(lst, keep_policy)
                losers = [u for u in lst if u.id != keeper.id]
                if not losers:
                    continue
                # Reasignar FKs (saltando modelos sin tabla)
                self._reassign_foreign_keys(keeper, losers)
                # Unir M2M (grupos y permisos)
                self._merge_user_m2m(keeper, losers)
                # BORRADO crudo con IDs literales (evita collector del ORM y bug en SQLite)
                try:
                    self._raw_delete_users([u.id for u in losers])
                except IntegrityError as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"No se pudo eliminar duplicados para '{email}' por restricción de integridad: {e}"
                        )
                    )
                    continue

        self.stdout.write(self.style.SUCCESS("Duplicados eliminados y relaciones reasignadas."))

        # 4) Índice único anti-duplicados
        self._ensure_unique_index(vendor)

    # ---------- helpers ----------

    def _choose_keeper(self, users_same_email, keep_policy):
        def sort_key(u):
            dj = u.date_joined or timezone.now()
            return (dj, u.id)

        if keep_policy == "superuser-first":
            sus = [u for u in users_same_email if u.is_superuser]
            if sus:
                return sorted(sus, key=sort_key, reverse=True)[0]
        return sorted(users_same_email, key=sort_key, reverse=True)[0]

    def _reassign_foreign_keys(self, keeper, losers):
        """
        Reasigna FKs a User -> keeper, pero SALTA modelos cuya tabla NO exista
        (útil si hay migraciones pendientes o tablas eliminadas) y tolera errores
        operacionales/programáticos. También borra O2O que apunten al 'loser'.
        """
        from django.apps import apps

        User = type(keeper)
        loser_ids = [u.id for u in losers]

        # Tablas existentes en esta BD
        try:
            existing_tables = set(connection.introspection.table_names())
        except Exception:
            existing_tables = set()

        for model in apps.get_models():
            if not model._meta.managed:
                continue
            if model._meta.db_table not in existing_tables:
                continue

            for field in model._meta.get_fields():
                if not getattr(field, "is_relation", False):
                    continue

                # FK a User -> update al keeper
                if getattr(field, "many_to_one", False) and getattr(field, "remote_field", None) and field.remote_field.model == User:
                    flt = {f"{field.name}__in": loser_ids}
                    upd = {f"{field.name}": keeper.id}
                    try:
                        model.objects.filter(**flt).update(**upd)
                    except (OperationalError, ProgrammingError):
                        continue

                # OneToOne a User -> borrar registros que apunten al loser
                if getattr(field, "one_to_one", False) and getattr(field, "remote_field", None) and field.remote_field.model == User:
                    flt = {f"{field.name}__in": loser_ids}
                    try:
                        model.objects.filter(**flt).delete()
                    except (OperationalError, ProgrammingError):
                        continue

    def _merge_user_m2m(self, keeper, losers):
        """Une grupos y permisos de los usuarios perdedores en el keeper."""
        try:
            for u in losers:
                for g in u.groups.all():
                    keeper.groups.add(g)
        except Exception:
            pass
        try:
            for u in losers:
                for p in u.user_permissions.all():
                    keeper.user_permissions.add(p)
        except Exception:
            pass

    def _raw_delete_users(self, ids):
        """Borra usuarios por id con SQL crudo SIN parámetros (IDs literales)."""
        if not ids:
            return
        ids_sql = ",".join(str(int(i)) for i in ids)  # IDs vienen de la BD -> int seguro
        sql = f"DELETE FROM auth_user WHERE id IN ({ids_sql})"
        with connection.cursor() as c:
            c.execute(sql)

    def _ensure_unique_index(self, vendor):
        self.stdout.write(self.style.MIGRATE_HEADING("==> Asegurando índice único case-insensitive por email"))
        try:
            if vendor == "postgresql":
                autocommit_before = connection.get_autocommit()
                if not autocommit_before:
                    connection.set_autocommit(True)
                try:
                    with connection.cursor() as c:
                        c.execute(
                            """
                            CREATE UNIQUE INDEX IF NOT EXISTS ux_auth_user_email_ci
                            ON auth_user (LOWER(email))
                            WHERE email IS NOT NULL AND btrim(email) <> '';
                            """
                        )
                finally:
                    connection.set_autocommit(autocommit_before)
            elif vendor == "sqlite":
                with connection.cursor() as c:
                    c.execute(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS ux_auth_user_email_ci
                        ON auth_user (email COLLATE NOCASE)
                        WHERE email IS NOT NULL AND trim(email) <> '';
                        """
                    )
            else:
                self.stdout.write(self.style.WARNING(f"Motor '{vendor}': omitiendo creación de índice automático."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"No se pudo crear el índice único: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS("Índice único verificado/creado."))
