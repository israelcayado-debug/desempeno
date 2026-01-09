import hashlib
import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


BLOCK_ORDER = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def safe_first_choice(model_field):
    choices = getattr(model_field, "choices", None) or []
    if choices:
        return choices[0][0]
    return None


class Command(BaseCommand):
    help = (
        "Importa una plantilla desde JSON normalizado a BD: "
        "EvaluationTemplate + TemplateSection + TemplateQuestion + TemplateActive + TemplateAssignment. "
        "DRY-RUN por defecto; usa --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Ruta al JSON (p.ej. P01_template.json)")
        parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD (si no, DRY-RUN).")
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Deja la nueva plantilla activa y actualiza TemplateActive.",
        )
        parser.add_argument(
            "--deactivate-previous",
            action="store_true",
            help="Desactiva otras plantillas con el mismo base_code (is_active=False).",
        )
        parser.add_argument(
            "--question-type",
            type=str,
            default="",
            help="Valor para TemplateQuestion.question_type. Si se omite, se usa el primer choice permitido.",
        )
        parser.add_argument(
            "--required",
            action="store_true",
            help="Marca todas las preguntas como requeridas si el modelo lo soporta.",
        )
        parser.add_argument(
            "--only-changed",
            action="store_true",
            help="Si el source_hash no cambia, omite la creacion de nueva version.",
        )
        parser.add_argument(
            "--skip-missing-position",
            action="store_true",
            help="Si no existe Position con code=base_code, omite TemplateAssignment en vez de fallar.",
        )

    def handle(self, *args, **opts):
        json_path = Path(opts["json_path"])
        if not json_path.exists():
            raise CommandError(f"No existe: {json_path}")

        apply_changes = bool(opts["apply"])
        activate = bool(opts["activate"])
        deactivate_previous = bool(opts["deactivate_previous"])
        force_required = bool(opts["required"])
        qt_override = (opts["question_type"] or "").strip()
        skip_missing_position = bool(opts["skip_missing_position"])
        only_changed = bool(opts["only_changed"])

        EvaluationTemplate = apps.get_model("templates_eval", "EvaluationTemplate")
        TemplateSection = apps.get_model("templates_eval", "TemplateSection")
        TemplateQuestion = apps.get_model("templates_eval", "TemplateQuestion")
        TemplateAssignment = apps.get_model("templates_eval", "TemplateAssignment")
        TemplateActive = apps.get_model("templates_eval", "TemplateActive")
        Position = apps.get_model("org", "Position")

        raw = json_path.read_text(encoding="utf-8")
        data = json.loads(raw)

        base_code = (data.get("base_code") or "").strip()
        blocks = data.get("blocks") or []
        if not base_code:
            raise CommandError("JSON invalido: falta base_code.")
        if not blocks:
            raise CommandError("JSON invalido: falta blocks.")

        source_hash = sha256_text(raw)

        last = EvaluationTemplate.objects.filter(base_code=base_code).order_by("-version").first()
        next_version = (last.version + 1) if last else 1

        qt_field = TemplateQuestion._meta.get_field("question_type")
        qt_final = qt_override or safe_first_choice(qt_field)
        if not qt_final:
            raise CommandError(
                "No puedo determinar question_type. Pasa --question-type con un valor valido "
                "(y si el campo tiene choices, usa uno de ellos)."
            )

        observed_codes = [str(b.get("code", "")).strip().upper() for b in blocks]
        missing_known = [c for c in ["A", "B", "C", "D", "E"] if c not in observed_codes]
        if missing_known:
            self.stdout.write(
                self.style.WARNING(
                    f"Aviso: faltan bloques esperados: {missing_known}. Se importara lo presente."
                )
            )

        has_is_required = any(f.name == "is_required" for f in TemplateQuestion._meta.fields)
        has_required = any(f.name == "required" for f in TemplateQuestion._meta.fields)

        created_count = 0
        skipped_unchanged = 0
        error_count = 0

        if only_changed and last and last.source_hash == source_hash:
            skipped_unchanged = 1
            self.stdout.write(
                self.style.WARNING(
                    f"SKIP (unchanged): base_code={base_code} version={last.version}"
                )
            )
            self.stdout.write(self.style.SUCCESS("RESUMEN"))
            self.stdout.write(f"  base_code: {base_code}")
            self.stdout.write(f"  created:   {created_count}")
            self.stdout.write(f"  skipped:   {skipped_unchanged}")
            self.stdout.write(f"  errors:    {error_count}")
            return

        ctx = transaction.atomic() if apply_changes else _noop_context()
        with ctx:
            tpl_kwargs = {
                "name": f"{base_code} v{next_version}",
                "base_code": base_code,
                "version": next_version,
                "is_active": True if activate else False,
                "source_hash": source_hash,
            }

            if not apply_changes:
                self.stdout.write(f"(dry) would create EvaluationTemplate: {tpl_kwargs}")
                tpl = type("Mock", (), {"pk": None, "base_code": base_code})()
            else:
                tpl = EvaluationTemplate.objects.create(**tpl_kwargs)
                created_count = 1

                if deactivate_previous and hasattr(EvaluationTemplate, "is_active"):
                    (
                        EvaluationTemplate.objects.filter(base_code=base_code)
                        .exclude(pk=tpl.pk)
                        .update(is_active=False)
                    )

            total_sections = 0
            total_questions = 0

            def block_sort_key(b):
                code = (b.get("code") or "").strip().upper()
                return BLOCK_ORDER.get(code, 999)

            def mk_section_title(b):
                code = (b.get("code") or "").strip().upper()
                title = (b.get("title") or "").strip()
                w = b.get("weight_percent")
                if w is not None:
                    return f"Bloque {code} - {title} ({w}%)"
                return f"Bloque {code} - {title}"

            for b in sorted(blocks, key=block_sort_key):
                code = (b.get("code") or "").strip().upper()
                items = b.get("items") or []
                sec_order = BLOCK_ORDER.get(code, total_sections + 1)
                sec_title = mk_section_title(b)

                if not apply_changes:
                    self.stdout.write(
                        f"(dry) would create TemplateSection: title={sec_title!r}, "
                        f"order={sec_order}, items={len(items)}"
                    )
                    total_sections += 1
                    total_questions += len(items)
                    continue

                section = TemplateSection.objects.create(
                    template=tpl,
                    title=sec_title,
                    order=sec_order,
                )
                total_sections += 1

                for i_order, it in enumerate(items, start=1):
                    sub = (it.get("subcriterion") or "").strip()
                    desc = (it.get("description") or "").strip()

                    if not sub and not desc:
                        continue

                    q_kwargs = {
                        "section": section,
                        "text": sub or desc,
                        "help_text": desc if sub else "",
                        "question_type": qt_final,
                        "order": i_order,
                    }
                    if force_required:
                        if has_is_required:
                            q_kwargs["is_required"] = True
                        if has_required:
                            q_kwargs["required"] = True

                    TemplateQuestion.objects.create(**q_kwargs)
                    total_questions += 1

            if apply_changes and activate:
                TemplateActive.objects.update_or_create(
                    base_code=base_code,
                    defaults={"template": tpl},
                )

                pos = Position.objects.filter(code=base_code).first()
                if not pos:
                    if skip_missing_position:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Position no existe para code={base_code!r}; se omite TemplateAssignment."
                            )
                        )
                    else:
                        raise CommandError(
                            f"No existe Position con code={base_code!r}. No puedo crear TemplateAssignment."
                        )
                else:
                    TemplateAssignment.objects.update_or_create(
                        template=tpl,
                        position=pos,
                        defaults={"is_default": True},
                    )

        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write(f"  base_code: {base_code}")
        self.stdout.write(f"  version:   {next_version}")
        self.stdout.write(f"  sections:  {total_sections}")
        self.stdout.write(f"  questions: {total_questions}")
        self.stdout.write(f"  question_type usado: {qt_final!r}")
        self.stdout.write(f"  created:   {created_count}")
        self.stdout.write(f"  skipped:   {skipped_unchanged}")
        self.stdout.write(f"  errors:    {error_count}")
        if not apply_changes:
            self.stdout.write(self.style.NOTICE("DRY-RUN: no se ha escrito nada. Usa --apply para aplicar."))


class _noop_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
