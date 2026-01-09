import csv
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.permissions import HR_ADMIN, MANAGER
from apps.evaluations.models import Evaluation, EvaluationItem, EvaluationPeriod
from apps.org.models import Department, Employee, Position


class ReportExportsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="mgr", password="x")
        self.hr_admin = User.objects.create_user(username="hr", password="x")
        Group.objects.get_or_create(name=MANAGER)[0].user_set.add(self.manager)
        Group.objects.get_or_create(name=HR_ADMIN)[0].user_set.add(self.hr_admin)

        self.department = Department.objects.create(name="Dept")
        self.position = Position.objects.create(
            code="P99",
            name="Pos",
            department=self.department,
            professional_group="GP1",
        )
        self.period = EvaluationPeriod.objects.create(
            name="2025 Anual",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )

    def _make_employee_eval(self, full_name, dni, manager):
        emp = Employee.objects.create(
            full_name=full_name,
            dni=dni,
            evaluation_position=self.position,
            manager=manager,
        )
        ev = Evaluation.objects.create(
            employee=emp,
            evaluator=self.manager,
            period=self.period,
            status=Evaluation.Status.DRAFT,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )
        return emp, ev

    def test_manager_scope_csv(self):
        emp1, _ = self._make_employee_eval("Alice", "DNI1", self.manager)
        emp2, _ = self._make_employee_eval("Bob", "DNI2", self.hr_admin)

        self.client.force_login(self.manager)
        url = reverse("report_period_export_csv", args=[self.period.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn(emp1.dni, content)
        self.assertNotIn(emp2.dni, content)

    def test_export_scope_page(self):
        for i in range(30):
            self._make_employee_eval(f"Emp {i:02d}", f"DNI{i:02d}", self.manager)

        self.client.force_login(self.manager)
        url = reverse("report_period_export_csv", args=[self.period.id])
        resp = self.client.get(
            url,
            {
                "page": "2",
                "page_size": "25",
                "export_scope": "page",
            },
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        reader = csv.reader(StringIO(content.lstrip("\ufeff")))
        rows = list(reader)
        # header + 5 rows
        self.assertEqual(len(rows), 6)

    def test_xlsx_limits(self):
        emp, ev = self._make_employee_eval("Alice", "DNI1", self.manager)
        EvaluationItem.objects.create(
            evaluation=ev,
            section_title="Bloque A",
            question_text="Q1",
            question_type="SCALE_1_5",
            is_required=True,
            display_order=1,
            value_scale=3,
        )

        self.client.force_login(self.manager)
        url = reverse("report_period_export_xlsx", args=[self.period.id])

        with mock.patch("apps.evaluations.views.EvaluationItem.objects.filter") as mocked:
            dummy = mock.Mock()
            dummy.select_related.return_value = dummy
            dummy.count.return_value = 50001
            mocked.return_value = dummy
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 400)

        with mock.patch("apps.evaluations.views.EvaluationItem.objects.filter") as mocked:
            dummy = mock.Mock()
            dummy.select_related.return_value = dummy
            dummy.count.return_value = 10001
            mocked.return_value = dummy
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Continuar de todos modos", resp.content)

    def test_xlsx_confirm_preserves_querystring(self):
        emp, ev = self._make_employee_eval("Alice", "DNI1", self.manager)
        EvaluationItem.objects.create(
            evaluation=ev,
            section_title="Bloque A",
            question_text="Q1",
            question_type="SCALE_1_5",
            is_required=True,
            display_order=1,
            value_scale=3,
        )

        self.client.force_login(self.manager)
        url = reverse("report_period_export_xlsx", args=[self.period.id])
        params = {
            "status": "DRAFT",
            "q": "Alice",
            "sort": "employee",
            "dir": "asc",
            "page_size": "25",
            "page": "2",
            "export_scope": "page",
        }

        with mock.patch("apps.evaluations.views.EvaluationItem.objects.filter") as mocked:
            dummy = mock.Mock()
            dummy.select_related.return_value = dummy
            dummy.count.return_value = 10001
            mocked.return_value = dummy
            resp = self.client.get(url, params)
            self.assertEqual(resp.status_code, 200)
            content = resp.content.decode("utf-8")
            self.assertIn("confirm=1", content)
            for key, val in params.items():
                self.assertIn(f"{key}={val}", content)


class EvaluationHistoryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="mgr2", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        Group.objects.get_or_create(name=MANAGER)[0].user_set.add(self.manager)

        self.department = Department.objects.create(name="DeptH")
        self.position = Position.objects.create(
            code="P98",
            name="Pos",
            department=self.department,
            professional_group="GP1",
        )
        self.period_1 = EvaluationPeriod.objects.create(
            name="2024",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        self.period_2 = EvaluationPeriod.objects.create(
            name="2025",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )
        self.employee = Employee.objects.create(
            full_name="Hist Emp",
            dni="HDNI1",
            evaluation_position=self.position,
            manager=self.manager,
        )
        self.eval_1 = Evaluation.objects.create(
            employee=self.employee,
            evaluator=self.manager,
            period=self.period_1,
            status=Evaluation.Status.SUBMITTED,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
            overall_comment="Global old",
        )
        self.eval_2 = Evaluation.objects.create(
            employee=self.employee,
            evaluator=self.manager,
            period=self.period_2,
            status=Evaluation.Status.DRAFT,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )
        EvaluationItem.objects.create(
            evaluation=self.eval_1,
            section_title="Bloque A",
            question_text="Q1",
            question_type="SCALE_1_5",
            is_required=True,
            display_order=1,
            value_scale=4,
        )
        EvaluationItem.objects.create(
            evaluation=self.eval_2,
            section_title="Bloque A",
            question_text="Q1",
            question_type="SCALE_1_5",
            is_required=True,
            display_order=1,
            value_scale=3,
        )
        from apps.evaluations.models import EvaluationBlockComment

        EvaluationBlockComment.objects.create(
            evaluation=self.eval_1,
            block_code="A",
            comment="Old block",
        )

    def test_history_excludes_current_period(self):
        self.client.force_login(self.manager)
        url = reverse("evaluate_employee", args=[self.employee.id, self.period_2.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("latin-1")
        self.assertIn(self.period_1.name, content)
        self.assertNotIn(self.period_2.name, content)

    def test_history_view_readonly(self):
        self.client.force_login(self.manager)
        url = reverse("evaluation_history_view", args=[self.eval_1.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 405)

    def test_history_respects_scope(self):
        other_emp = Employee.objects.create(
            full_name="Other Emp",
            dni="HDNI2",
            evaluation_position=self.position,
            manager=self.other,
        )
        other_eval = Evaluation.objects.create(
            employee=other_emp,
            evaluator=self.other,
            period=self.period_1,
            status=Evaluation.Status.DRAFT,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )
        self.client.force_login(self.manager)
        url = reverse("evaluation_history_view", args=[other_eval.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)


class EvaluationAlertsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username="mgr_alerts", password="x")
        Group.objects.get_or_create(name=MANAGER)[0].user_set.add(self.manager)

        self.department = Department.objects.create(name="DeptA")
        self.position = Position.objects.create(
            code="P97",
            name="Pos",
            department=self.department,
            professional_group="GP1",
        )

    def _make_employee(self, name, dni):
        return Employee.objects.create(
            full_name=name,
            dni=dni,
            evaluation_position=self.position,
            manager=self.manager,
        )

    def test_alerts_not_started_draft_blocked(self):
        today = timezone.now().date()
        period = EvaluationPeriod.objects.create(
            name="PeriodoA",
            start_date=today.replace(day=1),
            end_date=today.replace(day=28),
        )

        emp_no_eval = self._make_employee("Emp NoEval", "A001")
        emp_draft = self._make_employee("Emp Draft", "A002")
        emp_submitted = self._make_employee("Emp Sub", "A003")

        Evaluation.objects.create(
            employee=emp_draft,
            evaluator=self.manager,
            period=period,
            status=Evaluation.Status.DRAFT,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )
        Evaluation.objects.create(
            employee=emp_submitted,
            evaluator=self.manager,
            period=period,
            status=Evaluation.Status.SUBMITTED,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )

        self.client.force_login(self.manager)
        resp = self.client.get(reverse("my_team"))
        self.assertEqual(resp.status_code, 200)
        alerts = resp.context["alerts_by_employee_id"]

        codes_no_eval = {a["code"] for a in alerts[emp_no_eval.id]}
        self.assertIn("NOT_STARTED", codes_no_eval)

        codes_draft = {a["code"] for a in alerts[emp_draft.id]}
        self.assertIn("DRAFT", codes_draft)
        self.assertIn("MISSING_REQUIRED", codes_draft)
        self.assertNotIn("OVERDUE", codes_draft)

        codes_sub = {a["code"] for a in alerts[emp_submitted.id]}
        self.assertIn("BLOCKED", codes_sub)
        self.assertIn("MISSING_REQUIRED", codes_sub)

    def test_alert_overdue(self):
        past = timezone.now().date().replace(year=2024, month=1, day=15)
        period = EvaluationPeriod.objects.create(
            name="PeriodoOverdue",
            start_date=past.replace(day=1),
            end_date=past,
        )

        emp = self._make_employee("Emp Over", "A004")
        Evaluation.objects.create(
            employee=emp,
            evaluator=self.manager,
            period=period,
            status=Evaluation.Status.DRAFT,
            frozen_position_code=self.position.code,
            frozen_position_name=self.position.name,
        )

        self.client.force_login(self.manager)
        resp = self.client.get(reverse("my_team"))
        self.assertEqual(resp.status_code, 200)
        alerts = resp.context["alerts_by_employee_id"]
        codes = {a["code"] for a in alerts[emp.id]}
        self.assertIn("OVERDUE", codes)
        self.assertNotIn("DRAFT", codes)
