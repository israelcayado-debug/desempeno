from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.org.models import Position
from apps.templates_eval.models import EvaluationTemplate, TemplateActive, TemplateAssignment


class Command(BaseCommand):
    help = "Reporte de asignaciones Position -> plantilla y deteccion de huecos."

    def add_arguments(self, parser):
        parser.add_argument("--show-all", action="store_true", help="Muestra posiciones con asignacion OK.")
        parser.add_argument("--csv", action="store_true", help="Salida CSV.")

    def handle(self, *args, **options):
        show_all = bool(options["show_all"])
        as_csv = bool(options["csv"])

        positions = list(Position.objects.all().order_by("code"))
        assignments = TemplateAssignment.objects.select_related("template", "position").all()
        assign_map = {a.position_id: a.template.base_code for a in assignments}
        active_set = set(TemplateActive.objects.values_list("base_code", flat=True))

        rows = []
        missing_assignment = 0
        missing_active = 0

        for p in positions:
            base_code = assign_map.get(p.id)
            has_assignment = base_code is not None
            is_active = (base_code in active_set) if base_code else False

            status = "OK"
            if not has_assignment:
                status = "MISSING_ASSIGNMENT"
                missing_assignment += 1
            elif not is_active:
                status = "ASSIGNED_BUT_NOT_ACTIVE"
                missing_active += 1

            if show_all or status != "OK":
                rows.append(
                    {
                        "position_code": p.code,
                        "assigned_base_code": base_code or "",
                        "status": status,
                    }
                )

        position_codes = {p.code for p in positions}
        template_base_codes = set(
            EvaluationTemplate.objects.exclude(base_code="").values_list("base_code", flat=True).distinct()
        )
        base_codes_without_position = sorted(template_base_codes - position_codes)

        if as_csv:
            self.stdout.write("position_code,assigned_base_code,status")
            for r in rows:
                self.stdout.write(f'{r["position_code"]},{r["assigned_base_code"]},{r["status"]}')
            if base_codes_without_position:
                self.stdout.write("base_code_without_position,,")
                for code in base_codes_without_position:
                    self.stdout.write(f"{code},,NO_POSITION")
            return

        self.stdout.write("REPORTE ASIGNACIONES POSITION -> PLANTILLA")
        self.stdout.write(f"- Posiciones total: {len(positions)}")
        self.stdout.write(f"- Sin asignacion: {missing_assignment}")
        self.stdout.write(f"- Asignadas pero no activas: {missing_active}\n")

        for r in rows:
            self.stdout.write(f'- {r["position_code"]}: {r["assigned_base_code"]} [{r["status"]}]')

        if base_codes_without_position:
            self.stdout.write("\nBASE_CODE SIN POSITION")
            for code in base_codes_without_position:
                self.stdout.write(f"- {code}")
