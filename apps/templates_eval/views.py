import os
import tempfile
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.core.management import CommandError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from apps.templates_eval.management.commands.import_templates_docx import (
    derive_base_code_from_filename,
    parse_docx,
    template_fingerprint,
)
from apps.templates_eval.models import EvaluationTemplate, TemplateSection, TemplateQuestion


def health(request):
    return HttpResponse('ok')


@login_required
@require_http_methods(["GET", "POST"])
def import_template_docx(request):
    if not request.user.is_staff:
        raise PermissionDenied

    context = {}
    if request.method == "POST":
        docx_file = request.FILES.get("docx")
        base_code = (request.POST.get("base_code") or "").strip().upper()
        apply_import = request.POST.get("apply") == "1"

        if not docx_file:
            context["error"] = "Selecciona un archivo .docx."
        elif not docx_file.name.lower().endswith(".docx"):
            context["error"] = "El archivo debe ser .docx."
        else:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                    for chunk in docx_file.chunks():
                        tmp.write(chunk)
                    temp_path = tmp.name

                parsed = parse_docx(Path(temp_path))
                context["parsed"] = parsed

                if apply_import:
                    code = base_code or derive_base_code_from_filename(Path(docx_file.name))
                    fp = template_fingerprint(parsed)

                    existing_same = EvaluationTemplate.objects.filter(
                        base_code=code,
                        source_hash=fp,
                    ).first()
                    if existing_same:
                        context["warning"] = (
                            f"Ya existe {code} v{existing_same.version} con el mismo contenido."
                        )
                    else:
                        existing_versions = list(
                            EvaluationTemplate.objects.filter(base_code=code)
                            .values_list("version", flat=True)
                        )
                        new_version = max(existing_versions, default=0) + 1

                        with transaction.atomic():
                            tpl = EvaluationTemplate.objects.create(
                                name=parsed.name,
                                base_code=code,
                                version=new_version,
                                source_hash=fp,
                                is_active=False,
                            )

                            for s_idx, sec in enumerate(parsed.sections, start=1):
                                sec_obj = TemplateSection.objects.create(
                                    template=tpl,
                                    title=sec.name,
                                    order=s_idx,
                                )
                                for q_idx, q in enumerate(sec.questions, start=1):
                                    TemplateQuestion.objects.create(
                                        section=sec_obj,
                                        text=q.text,
                                        question_type=q.question_type,
                                        required=q.is_required,
                                        is_required=q.is_required,
                                        order=q_idx,
                                    )

                            if not EvaluationTemplate.objects.filter(
                                base_code=code,
                                is_active=True,
                            ).exists():
                                tpl.is_active = True
                                tpl.save(update_fields=["is_active"])

                        context["success"] = f"Importada {code}.v{new_version}."
                        context["base_code"] = code
            except CommandError as exc:
                context["error"] = str(exc)
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

    return render(request, "templates_eval/import_docx.html", context)
