from typing import Optional

from apps.templates_eval.models import EvaluationTemplate


def resolve_active_template(base_code: str) -> Optional[EvaluationTemplate]:
    base_code = (base_code or "").strip().upper()
    if not base_code:
        return None

    active = (
        EvaluationTemplate.objects
        .filter(base_code=base_code, is_active=True)
        .order_by("-version")
        .first()
    )
    if active:
        return active

    return (
        EvaluationTemplate.objects
        .filter(base_code=base_code)
        .order_by("-version")
        .first()
    )
