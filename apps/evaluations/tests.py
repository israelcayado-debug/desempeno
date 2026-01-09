import csv
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

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
