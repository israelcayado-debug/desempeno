from decimal import Decimal
from apps.evaluations.models import Evaluation
from apps.templates_eval.models import TemplateBlock, TemplateItem

def compute_final_score(evaluation: Evaluation) -> Decimal:
    scores = {s.template_item_id: Decimal(s.score) for s in evaluation.scores.all()}
    blocks = TemplateBlock.objects.filter(items__id__in=scores.keys()).distinct()

    total = Decimal("0")
    for block in blocks:
        items = TemplateItem.objects.filter(block=block).order_by("order")
        if not items:
            continue

        weights = []
        for it in items:
            w = it.item_weight
            weights.append(Decimal(w) if w is not None else None)

        if any(w is None for w in weights):
            n = Decimal(str(len(items)))
            weights = [Decimal("1") / n for _ in items]
        else:
            s_w = sum(weights) or Decimal("1")
            weights = [w / s_w for w in weights]

        block_score = Decimal("0")
        for it, w in zip(items, weights):
            block_score += (scores.get(it.id, Decimal("0")) * w)

        total += block_score * (Decimal(block.weight_percent) / Decimal("100"))

    return total
