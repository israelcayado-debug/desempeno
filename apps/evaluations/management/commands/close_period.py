from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.evaluations.models import EvaluationPeriod


class Command(BaseCommand):
    help = "Cierra un periodo de evaluacion (is_closed=True) y registra closed_at."

    def add_arguments(self, parser):
        parser.add_argument("period_id", type=int)

    def handle(self, *args, **options):
        period_id = options["period_id"]
        period = EvaluationPeriod.objects.filter(id=period_id).first()
        if not period:
            raise CommandError("No existe el periodo indicado.")

        if period.is_closed:
            self.stdout.write(self.style.WARNING("El periodo ya esta cerrado."))
            return

        period.is_closed = True
        period.closed_at = timezone.now()
        period.save(update_fields=["is_closed", "closed_at"])
        self.stdout.write(self.style.SUCCESS(f"Periodo cerrado: {period.id} - {period.name}"))
