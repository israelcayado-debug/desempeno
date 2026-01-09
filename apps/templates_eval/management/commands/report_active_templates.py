from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count, Max

from apps.templates_eval.models import EvaluationTemplate, TemplateActive, TemplateQuestion


class Command(BaseCommand):
    help = "Reporte de plantillas activas por base_code, con version y metricas basicas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-code",
            help="Filtra por un base_code concreto (p.ej. P02).",
            default=None,
        )
        parser.add_argument(
            "--csv",
            action="store_true",
            help="Salida en CSV (separador coma).",
        )

    def handle(self, *args, **options):
        base_code = (options["base_code"] or "").strip().upper()
        as_csv = bool(options["csv"])

        actives_qs = TemplateActive.objects.select_related("template").all()
        if base_code:
            actives_qs = actives_qs.filter(base_code=base_code)

        active_templates = [a.template for a in actives_qs if a.template_id]
        template_ids = [t.id for t in active_templates]
        if not template_ids:
            self.stdout.write("No hay plantillas activas para el filtro dado.")
            return

        q_counts = (
            TemplateQuestion.objects.filter(section__template_id__in=template_ids)
            .values("section__template_id")
            .annotate(total=Count("id"))
        )
        count_map = {row["section__template_id"]: row["total"] for row in q_counts}

        latest_by_base = (
            EvaluationTemplate.objects.values("base_code")
            .annotate(latest_version=Max("version"))
        )
        latest_map = {row["base_code"]: row["latest_version"] for row in latest_by_base}

        rows = []
        for a in actives_qs:
            t = a.template
            if not t:
                continue
            total_q = count_map.get(t.id, 0)
            latest_v = latest_map.get(t.base_code)
            rows.append(
                {
                    "base_code": t.base_code,
                    "active_version": t.version,
                    "latest_version": latest_v,
                    "is_latest_active": (latest_v == t.version),
                    "questions_total": total_q,
                    "template_id": t.id,
                    "source_hash": getattr(t, "source_hash", None),
                }
            )

        rows.sort(key=lambda r: r["base_code"])

        if as_csv:
            self.stdout.write(
                "base_code,active_version,latest_version,is_latest_active,questions_total,template_id,source_hash"
            )
            for r in rows:
                self.stdout.write(
                    f'{r["base_code"]},{r["active_version"]},{r["latest_version"]},'
                    f'{int(r["is_latest_active"])},{r["questions_total"]},'
                    f'{r["template_id"]},{r["source_hash"] or ""}'
                )
            return

        self.stdout.write("PLANTILLAS ACTIVAS")
        for r in rows:
            self.stdout.write(
                f'- {r["base_code"]}: activa v{r["active_version"]} '
                f'(ultima v{r["latest_version"]}, latest_active={r["is_latest_active"]}) '
                f'| preguntas={r["questions_total"]} | id={r["template_id"]}'
            )
