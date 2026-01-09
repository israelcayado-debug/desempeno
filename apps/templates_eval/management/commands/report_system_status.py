from __future__ import annotations

from collections import Counter
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Max

from apps.org.models import Position
from apps.templates_eval.models import (
    EvaluationTemplate,
    TemplateActive,
    TemplateAssignment,
    TemplateQuestion,
)


class Command(BaseCommand):
    help = "Reporte consolidado del estado del sistema de evaluacion del desempeno."

    def add_arguments(self, parser):
        parser.add_argument("--csv", action="store_true", help="Genera salida CSV resumida.")

    def handle(self, *args, **options):
        as_csv = bool(options["csv"])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        actives = TemplateActive.objects.select_related("template").all()
        active_templates = [a.template for a in actives if a.template_id]
        active_count = len(active_templates)
        active_base_codes = {t.base_code for t in active_templates if t.base_code}

        positions = list(Position.objects.all())
        position_count = len(positions)

        assignments = TemplateAssignment.objects.select_related("template").all()
        assign_map = {a.position_id: a.template.base_code for a in assignments}
        correct_assignments = sum(
            1 for p in positions if assign_map.get(p.id) in active_base_codes
        )

        latest_versions = (
            EvaluationTemplate.objects.values("base_code")
            .annotate(latest=Max("version"))
        )
        latest_map = {r["base_code"]: r["latest"] for r in latest_versions}

        outdated = []
        for t in active_templates:
            latest = latest_map.get(t.base_code)
            if latest is not None and latest != t.version:
                outdated.append((t.base_code, t.version, latest))

        q = TemplateQuestion.objects.filter(section__template__in=active_templates)
        q_types = sorted(set(q.values_list("question_type", flat=True)))
        q_counts = Counter(q.values_list("section__template__base_code", flat=True))
        count_values = sorted(set(q_counts.values()))
        count_min = min(count_values) if count_values else 0
        count_max = max(count_values) if count_values else 0

        missing_assignment = [p.code for p in positions if p.id not in assign_map]
        assigned_not_active = [
            (p.code, assign_map[p.id])
            for p in positions
            if p.id in assign_map and assign_map[p.id] not in active_base_codes
        ]

        position_codes = {p.code for p in positions}
        all_template_base_codes = set(
            EvaluationTemplate.objects.exclude(base_code="")
            .values_list("base_code", flat=True)
            .distinct()
        )
        legacy_base_codes = sorted(all_template_base_codes - position_codes)

        unexpected_types = [t for t in q_types if t != "SCALE_1_5"]

        self.stdout.write("REPORTE CONSOLIDADO - SISTEMA DE EVALUACION")
        self.stdout.write(f"Fecha: {now}\n")

        self.stdout.write("ESTADO GLOBAL")
        self.stdout.write(f"- Plantillas activas: {active_count}")
        self.stdout.write(f"- Posiciones totales: {position_count}")
        self.stdout.write(f"- Asignaciones correctas: {correct_assignments}\n")

        self.stdout.write("VERSIONADO")
        if outdated:
            for bc, v_act, v_last in outdated:
                self.stdout.write(f"- {bc}: activa v{v_act}, ultima v{v_last}")
        else:
            self.stdout.write("- Todas las activas estan en ultima version")
        self.stdout.write("")

        self.stdout.write("ESTRUCTURA DE PREGUNTAS")
        types_label = ", ".join(q_types) if q_types else "(sin datos)"
        self.stdout.write(f"- Tipos detectados: {types_label}")
        if unexpected_types:
            self.stdout.write(f"- Alerta: tipos no esperados: {', '.join(unexpected_types)}")
        self.stdout.write(
            f"- Recuentos por plantilla: min={count_min}, max={count_max}, valores={count_values}"
        )
        self.stdout.write("")

        self.stdout.write("ASIGNACIONES")
        self.stdout.write(f"- Posiciones sin asignacion: {len(missing_assignment)}")
        for code in missing_assignment:
            self.stdout.write(f"  * {code}")
        self.stdout.write(f"- Asignadas pero no activas: {len(assigned_not_active)}")
        for code, bc in assigned_not_active:
            self.stdout.write(f"  * {code} -> {bc}")
        self.stdout.write(f"- Base_code sin Position: {len(legacy_base_codes)}")
        for bc in legacy_base_codes:
            self.stdout.write(f"  * {bc}")

        issues = bool(outdated or missing_assignment or assigned_not_active or unexpected_types)
        self.stdout.write("\nCONCLUSION")
        self.stdout.write("ESTADO: " + ("ATENCION" if issues else "OK"))

        actions = []
        if outdated:
            actions.append("Revisar y activar la ultima version en base_code desfasados.")
        if missing_assignment:
            actions.append("Asignar plantilla a posiciones sin asignacion.")
        if assigned_not_active:
            actions.append("Activar plantillas usadas en asignaciones o corregir asignaciones.")
        if unexpected_types:
            actions.append("Revisar tipos de pregunta fuera de SCALE_1_5.")

        if actions:
            self.stdout.write("SUGERENCIAS")
            for action in actions:
                self.stdout.write(f"- {action}")

        if as_csv:
            self.stdout.write("\nCSV")
            self.stdout.write("metric,value")
            self.stdout.write(f"active_templates,{active_count}")
            self.stdout.write(f"positions_total,{position_count}")
            self.stdout.write(f"correct_assignments,{correct_assignments}")
            self.stdout.write(f"outdated_templates,{len(outdated)}")
            self.stdout.write(f"positions_without_assignment,{len(missing_assignment)}")
            self.stdout.write(f"assigned_not_active,{len(assigned_not_active)}")
            self.stdout.write(f"legacy_base_codes,{len(legacy_base_codes)}")
            self.stdout.write(f"unexpected_question_types,{len(unexpected_types)}")
