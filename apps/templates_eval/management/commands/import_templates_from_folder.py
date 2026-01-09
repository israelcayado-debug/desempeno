import re
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


BASE_CODE_RE = re.compile(r"^(P\d{2})_", re.IGNORECASE)


class Command(BaseCommand):
    help = (
        "Importa plantillas DOCX desde una carpeta completa. "
        "Extrae base_code del nombre (PXX_), genera JSON y lo importa a BD. "
        "DRY-RUN por defecto."
    )

    def add_arguments(self, parser):
        parser.add_argument("input_dir", type=str, help="Carpeta con archivos .docx")
        parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD")
        parser.add_argument("--activate", action="store_true", help="Activa la nueva version por base_code")
        parser.add_argument("--deactivate-previous", action="store_true", help="Desactiva versiones anteriores")
        parser.add_argument("--required", action="store_true", help="Marca todas las preguntas como requeridas")
        parser.add_argument(
            "--question-type",
            type=str,
            required=True,
            help="Valor de TemplateQuestion.question_type (p.ej. SCALE_1_5)",
        )
        parser.add_argument(
            "--json-dir",
            type=str,
            default="generated_templates",
            help="Carpeta donde se generaran los JSON intermedios",
        )
        parser.add_argument(
            "--only-changed",
            action="store_true",
            help="No crea nueva version si source_hash no cambia.",
        )
        parser.add_argument(
            "--skip-missing-position",
            action="store_true",
            help="Omite TemplateAssignment si no existe Position con el base_code.",
        )

    def handle(self, *args, **opts):
        input_dir = Path(opts["input_dir"])
        if not input_dir.exists() or not input_dir.is_dir():
            raise CommandError(f"No es una carpeta valida: {input_dir}")

        json_dir = Path(opts["json_dir"])
        json_dir.mkdir(parents=True, exist_ok=True)

        apply_changes = bool(opts["apply"])

        files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() == ".docx")

        if not files:
            raise CommandError("No se encontraron archivos .docx")

        ok = []
        failed = []

        self.stdout.write(f"Procesando {len(files)} archivos. apply={apply_changes}")

        for docx in files:
            m = BASE_CODE_RE.match(docx.name)
            if not m:
                failed.append((docx.name, "No se pudo extraer base_code"))
                continue

            base_code = m.group(1).upper()
            json_path = json_dir / f"{base_code}.json"

            self.stdout.write(f"\\n[{base_code}] {docx.name}")

            try:
                subprocess.check_call(
                    [
                        sys.executable,
                        "tools/extract_template_docx.py",
                        str(docx),
                        base_code,
                        str(json_path),
                    ]
                )

                cmd = [
                    sys.executable,
                    "manage.py",
                    "import_template_json",
                    str(json_path),
                    "--question-type",
                    opts["question_type"],
                ]

                if opts["required"]:
                    cmd.append("--required")
                if opts["activate"]:
                    cmd.append("--activate")
                if opts["deactivate_previous"]:
                    cmd.append("--deactivate-previous")
                if opts["only_changed"]:
                    cmd.append("--only-changed")
                if opts["skip_missing_position"]:
                    cmd.append("--skip-missing-position")
                if apply_changes:
                    cmd.append("--apply")

                subprocess.check_call(cmd)

                ok.append(base_code)

            except subprocess.CalledProcessError as e:
                failed.append((docx.name, str(e)))

        self.stdout.write("\\nRESUMEN FINAL")
        self.stdout.write(f"  OK:     {len(ok)} -> {ok}")
        self.stdout.write(f"  FALLO:  {len(failed)}")

        if failed:
            self.stdout.write("\\nDETALLE DE ERRORES")
            for f, err in failed:
                self.stdout.write(f"  - {f}: {err}")
