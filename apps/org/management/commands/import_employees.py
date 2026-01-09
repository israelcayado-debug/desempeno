import csv
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.org.models import Employee, Position  # ajusta si tu import real difiere


REQUIRED_COLUMNS = {"dni", "full_name", "evaluation_position_code"}


@dataclass
class RowResult:
    action: str  # "create" | "update" | "skip" | "error"
    dni: str
    message: str = ""


class Command(BaseCommand):
    help = "Importa empleados desde CSV (upsert por DNI). DRY-RUN por defecto; usar --apply para escribir."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Ruta al CSV (recomendado UTF-8 y delimitador ';').")
        parser.add_argument("--apply", action="store_true", help="Aplica cambios en BD (si no, solo DRY-RUN).")
        parser.add_argument("--delimiter", type=str, default=";", help="Delimitador CSV. Por defecto ';'.")
        parser.add_argument("--encoding", type=str, default="utf-8-sig", help="Encoding. Por defecto utf-8-sig.")
        parser.add_argument("--strict", action="store_true", help="Si hay un error en una fila, aborta todo.")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"No existe el archivo: {csv_path}")

        apply_changes = bool(options["apply"])
        delimiter = options["delimiter"]
        encoding = options["encoding"]
        strict = bool(options["strict"])

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Import employees | file={csv_path} | apply={apply_changes} | delimiter={delimiter!r} | encoding={encoding}"
            )
        )

        creates = updates = skips = errors = 0
        results: list[RowResult] = []

        with csv_path.open("r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            if not reader.fieldnames:
                raise CommandError("CSV sin cabeceras (header).")

            fieldnames = {h.strip() for h in reader.fieldnames}
            missing = REQUIRED_COLUMNS - fieldnames
            if missing:
                raise CommandError(f"Faltan columnas obligatorias: {sorted(missing)}")

            ctx = transaction.atomic() if apply_changes else _noop_context()
            with ctx:
                for line_no, row in enumerate(reader, start=2):  # 1=header
                    try:
                        r = self._process_row(row, apply_changes)
                        results.append(r)

                        if r.action == "create":
                            creates += 1
                        elif r.action == "update":
                            updates += 1
                        elif r.action == "skip":
                            skips += 1
                        else:
                            errors += 1
                            if strict:
                                raise CommandError(f"Fila {line_no}: {r.message}")

                    except Exception as e:
                        errors += 1
                        msg = f"Fila {line_no}: {e}"
                        results.append(RowResult(action="error", dni=(row.get("dni") or "").strip(), message=msg))
                        if strict:
                            raise

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write(f"  create: {creates}")
        self.stdout.write(f"  update: {updates}")
        self.stdout.write(f"  skip:   {skips}")
        self.stdout.write(f"  errors: {errors}")

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("ERRORES (primeros 20):"))
            shown = 0
            for r in results:
                if r.action == "error":
                    self.stdout.write(f"  - {r.message}")
                    shown += 1
                    if shown >= 20:
                        break

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("DRY-RUN: no se ha escrito nada. Usa --apply para aplicar."))

    def _process_row(self, row: dict, apply_changes: bool) -> RowResult:
        dni = (row.get("dni") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        pos_code = (row.get("evaluation_position_code") or "").strip()

        if not dni:
            return RowResult(action="error", dni="", message="DNI vacio")
        if not full_name:
            return RowResult(action="error", dni=dni, message="full_name vacio")
        if not pos_code:
            return RowResult(action="error", dni=dni, message="evaluation_position_code vacio")

        position = Position.objects.filter(code=pos_code).first()
        if not position:
            return RowResult(action="error", dni=dni, message=f"Position no existe para code={pos_code!r}")

        emp = Employee.objects.filter(dni=dni).first()

        if emp is None:
            if not apply_changes:
                return RowResult(action="create", dni=dni, message="(dry) would create")

            emp = Employee(
                dni=dni,
                full_name=full_name,
                evaluation_position=position,
            )
            emp.save()
            return RowResult(action="create", dni=dni, message="created")

        changed = False
        if emp.full_name != full_name:
            emp.full_name = full_name
            changed = True
        if emp.evaluation_position_id != position.id:
            emp.evaluation_position = position
            changed = True

        if not changed:
            return RowResult(action="skip", dni=dni, message="no changes")

        if not apply_changes:
            return RowResult(action="update", dni=dni, message="(dry) would update")

        emp.save()
        return RowResult(action="update", dni=dni, message="updated")


class _noop_context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
