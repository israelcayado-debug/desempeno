from django.core.management.base import BaseCommand, CommandError

from apps.evaluations.models import EvaluationPeriod


class Command(BaseCommand):
    help = "Abre un periodo de evaluacion (is_closed=False) y limpia closed_at."

    def add_arguments(self, parser):
        parser.add_argument("period_id", type=int)

    def handle(self, *args, **options):
        period_id = options["period_id"]
        period = EvaluationPeriod.objects.filter(id=period_id).first()
        if not period:
            raise CommandError("No existe el periodo indicado.")

        if not period.is_closed:
            self.stdout.write(self.style.WARNING("El periodo ya esta abierto."))
            return

        period.is_closed = False
        period.closed_at = None
        period.save(update_fields=["is_closed", "closed_at"])
        self.stdout.write(self.style.SUCCESS(f"Periodo abierto: {period.id} - {period.name}"))
