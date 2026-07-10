from decimal import Decimal
from django.test import TestCase, Client as HttpClient
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Client, Payment


class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_str(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("100.00"), date_issued="2026-01-01"
        )
        self.assertIn("100.00", str(p))
        self.assertIn("Acme Corp", str(p))

    def test_default_status_is_pending(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("50.00"), date_issued="2026-01-01"
        )
        self.assertEqual(p.status, "pending")

    def test_date_paid_optional(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("75.00"), date_issued="2026-01-01"
        )
        self.assertIsNone(p.date_paid)


class PaymentViewTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.http.login(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_log_payment_get(self):
        url = reverse("log_payment", args=[self.client_obj.id])
        response = self.http.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Corp")

    def test_log_payment_post_creates_payment(self):
        url = reverse("log_payment", args=[self.client_obj.id])
        response = self.http.post(url, {
            "amount": "200.00",
            "date_issued": "2026-06-01",
            "date_paid": "",
            "status": "pending",
            "description": "Invoice #001",
        })
        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        self.assertEqual(Payment.objects.count(), 1)
        p = Payment.objects.first()
        self.assertEqual(p.amount, Decimal("200.00"))
        self.assertEqual(p.client, self.client_obj)
        self.assertEqual(p.description, "Invoice #001")

    def test_log_payment_requires_login(self):
        self.http.logout()
        url = reverse("log_payment", args=[self.client_obj.id])
        response = self.http.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_log_payment_rejects_other_users_client(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Corp")
        url = reverse("log_payment", args=[other_client.id])
        response = self.http.post(url, {
            "amount": "100.00",
            "date_issued": "2026-06-01",
            "status": "pending",
        })
        self.assertEqual(response.status_code, 404)

    def test_delete_payment_post(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("100.00"), date_issued="2026-01-01"
        )
        url = reverse("delete_payment", args=[p.id])
        response = self.http.post(url)
        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        self.assertEqual(Payment.objects.count(), 0)

    def test_delete_payment_get_shows_confirmation(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("100.00"), date_issued="2026-01-01"
        )
        url = reverse("delete_payment", args=[p.id])
        response = self.http.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100")

    def test_delete_payment_rejects_other_users_payment(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Corp")
        p = Payment.objects.create(
            client=other_client, amount=Decimal("100.00"), date_issued="2026-01-01"
        )
        url = reverse("delete_payment", args=[p.id])
        response = self.http.post(url)
        self.assertEqual(response.status_code, 404)

    def test_edit_payment_get_prefills_form(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("250.00"),
            date_issued="2026-03-01", status="pending", description="Invoice #002"
        )
        url = reverse("edit_payment", args=[p.id])
        response = self.http.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "250")
        self.assertContains(response, "Invoice #002")

    def test_edit_payment_post_updates_payment(self):
        p = Payment.objects.create(
            client=self.client_obj, amount=Decimal("250.00"),
            date_issued="2026-03-01", status="pending"
        )
        url = reverse("edit_payment", args=[p.id])
        response = self.http.post(url, {
            "amount": "300.00",
            "date_issued": "2026-03-01",
            "date_paid": "2026-06-10",
            "status": "paid",
            "description": "Updated",
        })
        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        p.refresh_from_db()
        self.assertEqual(p.amount, Decimal("300.00"))
        self.assertEqual(p.status, "paid")
        self.assertEqual(p.description, "Updated")

    def test_edit_payment_rejects_other_users_payment(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Corp")
        p = Payment.objects.create(
            client=other_client, amount=Decimal("100.00"), date_issued="2026-01-01"
        )
        url = reverse("edit_payment", args=[p.id])
        response = self.http.post(url, {
            "amount": "999.00", "date_issued": "2026-01-01", "status": "paid"
        })
        self.assertEqual(response.status_code, 404)


class ClientDetailPaymentSummaryTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.http.login(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_totals_displayed(self):
        Payment.objects.create(client=self.client_obj, amount=Decimal("300.00"), date_issued="2026-01-01", status="paid")
        Payment.objects.create(client=self.client_obj, amount=Decimal("150.00"), date_issued="2026-02-01", status="pending")
        Payment.objects.create(client=self.client_obj, amount=Decimal("50.00"), date_issued="2026-03-01", status="overdue")

        url = reverse("client_detail", args=[self.client_obj.id])
        response = self.http.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_paid"], Decimal("300.00"))
        self.assertEqual(response.context["total_outstanding"], Decimal("200.00"))

    def test_zero_totals_when_no_payments(self):
        url = reverse("client_detail", args=[self.client_obj.id])
        response = self.http.get(url)
        self.assertEqual(response.context["total_paid"], 0)
        self.assertEqual(response.context["total_outstanding"], 0)
