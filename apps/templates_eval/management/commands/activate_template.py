from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.templates_eval.models import EvaluationTemplate


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("base_code")
        parser.add_argument("version", type=int)

    def handle(self, *args, **opts):
        base = (opts["base_code"] or "").strip().upper()
        ver = opts["version"]

        tpl = EvaluationTemplate.objects.filter(base_code=base, version=ver).first()
        if not tpl:
            raise CommandError("No existe esa plantilla.")

        with transaction.atomic():
            EvaluationTemplate.objects.filter(base_code=base, is_active=True).update(is_active=False)
            tpl.is_active = True
            tpl.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS(f"Activa: {base} v{ver}"))
