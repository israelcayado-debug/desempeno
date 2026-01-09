from django.apps import apps


ET = apps.get_model("templates_eval", "EvaluationTemplate")
TA = apps.get_model("templates_eval", "TemplateActive")
TS = apps.get_model("templates_eval", "TemplateSection")
TQ = apps.get_model("templates_eval", "TemplateQuestion")
TAS = apps.get_model("templates_eval", "TemplateAssignment")
Position = apps.get_model("org", "Position")


base_codes = [f"P{str(i).zfill(2)}" for i in range(1, 36)]

rows = []
issues = []
warnings = []

for bc in base_codes:
    active = ET.objects.filter(base_code=bc, is_active=True).order_by("-version").first()
    ta = TA.objects.filter(base_code=bc).first()

    pos = Position.objects.filter(code=bc).first()
    tas = None
    if pos:
        tas = TAS.objects.filter(position=pos, is_default=True).order_by("-id").first()

    sections = TS.objects.filter(template=active).count() if active else 0
    questions = TQ.objects.filter(section__template=active).count() if active else 0

    rows.append(
        {
            "base_code": bc,
            "active_tpl_id": active.id if active else None,
            "active_version": active.version if active else None,
            "TemplateActive_tpl_id": ta.template_id if ta else None,
            "Position_exists": bool(pos),
            "TemplateAssignment_tpl_id": tas.template_id if tas else None,
            "sections": sections,
            "questions": questions,
        }
    )

    if not active:
        issues.append((bc, "NO active EvaluationTemplate"))
    if ta and active and ta.template_id != active.id:
        issues.append((bc, f"TemplateActive apunta a {ta.template_id} pero active es {active.id}"))
    if active and sections != 5:
        issues.append((bc, f"Estructura inesperada: sections={sections}"))
    if active and questions == 0:
        issues.append((bc, "Estructura inesperada: questions=0"))
    if active and 0 < questions < 10:
        warnings.append((bc, f"Preguntas bajas: questions={questions}"))
    if pos and (not tas or (active and tas.template_id != active.id)):
        issues.append((bc, "Position existe pero TemplateAssignment default falta o no apunta a la activa"))

print("RESUMEN (primeros 10):")
for r in rows[:10]:
    print(r)

print("\nTOTALES:")
print("  base_codes:", len(rows))
print("  con active:", sum(1 for r in rows if r["active_tpl_id"]))
print("  con TA:", sum(1 for r in rows if r["TemplateActive_tpl_id"]))
print("  con Position:", sum(1 for r in rows if r["Position_exists"]))
print("  con Assignment:", sum(1 for r in rows if r["TemplateAssignment_tpl_id"]))

print("\nISSUES:", len(issues))
for bc, msg in issues[:50]:
    print(" ", bc, "-", msg)

print("\nWARNINGS:", len(warnings))
for bc, msg in warnings[:50]:
    print(" ", bc, "-", msg)
