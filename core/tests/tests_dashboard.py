from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from core.models import Appointment, Client, Payment, TimeLog


class DashboardViewTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.http.login(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")
        self.other_client = Client.objects.create(owner=self.other_user, name="Other Corp")

    def test_dashboard_requires_login(self):
        self.http.logout()

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_displays_summary_metrics(self, mock_localdate):
        TimeLog.objects.create(
            client=self.client_obj,
            date=date(2026, 7, 5),
            hours=Decimal("5.00"),
            description="Logo work",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("500.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 10),
            status="paid",
        )
        completed_appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Completed Session",
            date=date(2026, 7, 8),
            start_time=time(9, 0),
            end_time=time(10, 0),
            price=Decimal("200.00"),
            status="completed",
        )
        Payment.objects.create(
            client=self.client_obj,
            appointment=completed_appointment,
            amount=Decimal("200.00"),
            date_issued=date(2026, 7, 8),
            status="pending",
        )
        Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Today",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
            price=Decimal("100.00"),
            status="upcoming",
        )
        Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="This Week",
            date=date(2026, 7, 18),
            start_time=time(9, 0),
            price=Decimal("300.00"),
            status="upcoming",
        )

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_hours_this_month"], Decimal("5.00"))
        self.assertEqual(response.context["total_paid_this_month"], Decimal("500.00"))
        self.assertEqual(response.context["effective_hourly_rate"], Decimal("100.00"))
        self.assertEqual(response.context["completed_but_unpaid"], Decimal("200.00"))
        self.assertEqual(response.context["upcoming_revenue"], Decimal("400.00"))
        self.assertEqual(response.context["appointments_today"].count(), 1)
        self.assertEqual(response.context["upcoming_appointments"].count(), 2)

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_ignores_other_users_data(self, mock_localdate):
        TimeLog.objects.create(
            client=self.other_client,
            date=date(2026, 7, 5),
            hours=Decimal("99.00"),
            description="Private work",
        )
        Payment.objects.create(
            client=self.other_client,
            amount=Decimal("999.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 10),
            status="paid",
        )
        Appointment.objects.create(
            client=self.other_client,
            owner=self.other_user,
            title="Other User Appointment",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
            price=Decimal("999.00"),
            status="upcoming",
        )

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.context["total_hours_this_month"], Decimal("0"))
        self.assertEqual(response.context["total_paid_this_month"], Decimal("0"))
        self.assertEqual(response.context["effective_hourly_rate"], Decimal("0"))
        self.assertEqual(response.context["upcoming_revenue"], Decimal("0"))
        self.assertEqual(response.context["appointments_today"].count(), 0)
        self.assertEqual(response.context["upcoming_appointments"].count(), 0)

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_chart_data_defaults_to_past_three_months(self, mock_localdate):
        TimeLog.objects.create(
            client=self.client_obj,
            date=date(2026, 5, 5),
            hours=Decimal("1.00"),
            description="May work",
        )
        TimeLog.objects.create(
            client=self.client_obj,
            date=date(2026, 6, 5),
            hours=Decimal("2.00"),
            description="June work",
        )
        TimeLog.objects.create(
            client=self.client_obj,
            date=date(2026, 7, 5),
            hours=Decimal("3.00"),
            description="July work",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("100.00"),
            date_issued=date(2026, 5, 1),
            date_paid=date(2026, 5, 10),
            status="paid",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("300.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 10),
            status="paid",
        )

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.context["selected_hours_range"], "3")
        self.assertEqual(response.context["chart_data"]["labels"], ["May 26", "Jun 26", "Jul 26"])
        self.assertEqual(response.context["chart_data"]["hours"], [1.0, 2.0, 3.0])
        self.assertEqual(response.context["chart_data"]["paid"], [100.0, 0.0, 300.0])

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_accepts_twelve_month_chart_range(self, mock_localdate):
        response = self.http.get(reverse("dashboard"), {"hours_range": "12"})

        self.assertEqual(response.context["selected_hours_range"], "12")
        self.assertEqual(len(response.context["chart_data"]["labels"]), 12)
        self.assertEqual(response.context["chart_data"]["labels"][0], "Aug 25")
        self.assertEqual(response.context["chart_data"]["labels"][-1], "Jul 26")

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_invalid_chart_range_falls_back_to_three_months(self, mock_localdate):
        response = self.http.get(reverse("dashboard"), {"hours_range": "99"})

        self.assertEqual(response.context["selected_hours_range"], "3")
        self.assertEqual(len(response.context["chart_data"]["labels"]), 3)

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_payment_pie_data_groups_status_totals(self, mock_localdate):
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("300.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 10),
            status="paid",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("150.00"),
            date_issued=date(2026, 7, 1),
            status="pending",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("50.00"),
            date_issued=date(2026, 7, 1),
            status="overdue",
        )

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.context["payment_pie_data"]["labels"], ["Paid", "Outstanding", "Overdue"])
        self.assertEqual(response.context["payment_pie_data"]["values"], [300.0, 150.0, 50.0])

    @patch("core.views.timezone.localdate", return_value=date(2026, 7, 15))
    def test_dashboard_calculates_average_days_to_payment(self, mock_localdate):
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("100.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 5),
            status="paid",
        )
        Payment.objects.create(
            client=self.client_obj,
            amount=Decimal("200.00"),
            date_issued=date(2026, 7, 1),
            date_paid=date(2026, 7, 7),
            status="paid",
        )

        response = self.http.get(reverse("dashboard"))

        self.assertEqual(response.context["average_days_to_payment"], 5)
