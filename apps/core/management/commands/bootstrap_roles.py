from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.core.permissions import EXEC, HR, HR_ADMIN, MANAGER


class Command(BaseCommand):
    help = "Crea grupos base del sistema si no existen."

    def handle(self, *args, **options):
        groups = [HR, HR_ADMIN, EXEC, MANAGER]
        created = []
        for name in groups:
            obj, was_created = Group.objects.get_or_create(name=name)
            if was_created:
                created.append(obj.name)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Grupos creados: {', '.join(created)}"))
        else:
            self.stdout.write(self.style.WARNING("Los grupos ya existian."))
