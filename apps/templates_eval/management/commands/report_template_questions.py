from __future__ import annotations

import re
from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.templates_eval.models import TemplateActive, TemplateQuestion


SECTION_CODE_RE = re.compile(r"^Bloque\s+([A-Z])\b", re.IGNORECASE)


def section_code_from_title(title: str) -> str:
    m = SECTION_CODE_RE.match(title or "")
    return (m.group(1).upper() if m else "UNK")


class Command(BaseCommand):
    help = "Reporte de preguntas por seccion (A-E) con desglose por tipo."

    def add_arguments(self, parser):
        parser.add_argument("--base-code", default=None, help="Filtra por base_code (p.ej. P10).")
        parser.add_argument(
            "--only-active",
            action="store_true",
            help="Solo reporta plantillas activas (recomendado).",
        )

    def handle(self, *args, **options):
        base_code = (options["base_code"] or "").strip().upper()
        only_active = bool(options["only_active"])

        template_ids = None
        base_codes = None

        if only_active:
            qs = TemplateActive.objects.select_related("template").all()
            if base_code:
                qs = qs.filter(base_code=base_code)
            templates = [a.template for a in qs if a.template_id]
            template_ids = [t.id for t in templates]
            base_codes = {t.id: t.base_code for t in templates}
            if not template_ids:
                self.stdout.write("No hay plantillas activas para el filtro dado.")
                return

        q = TemplateQuestion.objects.select_related("section", "section__template").all()

        if only_active:
            q = q.filter(section__template_id__in=template_ids)
        if base_code and not only_active:
            q = q.filter(section__template__base_code=base_code)

        data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        totals = defaultdict(int)
        inferred_base_codes = {}

        for question in q.iterator():
            section = question.section
            template = section.template
            tid = template.id
            inferred_base_codes[tid] = template.base_code
            sec_code = section_code_from_title(section.title)
            qtype = question.question_type
            data[tid][sec_code][qtype] += 1
            totals[tid] += 1

        if not data:
            self.stdout.write("No hay preguntas para el filtro dado.")
            return

        if not base_codes:
            base_codes = inferred_base_codes

        def sort_key(tid):
            return (base_codes.get(tid, ""), tid)

        for tid in sorted(data.keys(), key=sort_key):
            label = base_codes.get(tid, f"template_id={tid}")
            self.stdout.write(f"\n{label} | TOTAL preguntas: {totals[tid]}")
            for sec in sorted(data[tid].keys()):
                bucket = data[tid][sec]
                self.stdout.write(
                    f"  - Seccion {sec}: "
                    f"SCALE_1_5={bucket.get('SCALE_1_5', 0)}, "
                    f"YES_NO={bucket.get('YES_NO', 0)}, "
                    f"TEXT={bucket.get('TEXT', 0)}"
                )
