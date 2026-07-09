from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from core.models import Appointment, Client, Payment, TimeLog
from core.views import appointment_duration_hours


class AppointmentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_default_status_is_upcoming(self):
        appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )

        self.assertEqual(appointment.status, "upcoming")

    def test_default_price_is_zero(self):
        appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )
        appointment.refresh_from_db()

        self.assertEqual(appointment.price, Decimal("0.00"))

    def test_end_time_is_optional(self):
        appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )

        self.assertIsNone(appointment.end_time)


class AppointmentLogicTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_duration_hours_returns_decimal_hours(self):
        appointment = Appointment(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
            end_time=time(10, 30),
        )

        self.assertEqual(appointment_duration_hours(appointment), Decimal("1.50"))

    def test_duration_hours_returns_none_without_end_time(self):
        appointment = Appointment(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )

        self.assertIsNone(appointment_duration_hours(appointment))

    def test_duration_hours_returns_none_when_end_time_is_before_start_time(self):
        appointment = Appointment(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(10, 0),
            end_time=time(9, 30),
        )

        self.assertIsNone(appointment_duration_hours(appointment))


class AppointmentViewTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.http.login(username="testuser", password="pass")
        self.client_obj = Client.objects.create(owner=self.user, name="Acme Corp")

    def test_add_appointment_get(self):
        response = self.http.get(reverse("add_appointment", args=[self.client_obj.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Appointment for Acme Corp")

    def test_add_appointment_post_creates_appointment(self):
        response = self.http.post(reverse("add_appointment", args=[self.client_obj.id]), {
            "title": "Consultation",
            "date": "2026-07-15",
            "start_time": "09:00",
            "end_time": "",
            "price": "150.00",
            "status": "upcoming",
            "notes": "Discovery call",
        })

        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        self.assertEqual(Appointment.objects.count(), 1)

        appointment = Appointment.objects.first()
        self.assertEqual(appointment.client, self.client_obj)
        self.assertEqual(appointment.owner, self.user)
        self.assertEqual(appointment.title, "Consultation")
        self.assertEqual(appointment.price, Decimal("150.00"))

    def test_completed_appointment_creates_time_log_and_payment(self):
        response = self.http.post(reverse("add_appointment", args=[self.client_obj.id]), {
            "title": "Strategy Session",
            "date": "2026-07-15",
            "start_time": "09:00",
            "end_time": "10:30",
            "price": "200.00",
            "status": "completed",
            "notes": "",
        })

        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        appointment = Appointment.objects.get(title="Strategy Session")

        self.assertEqual(TimeLog.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        time_log = TimeLog.objects.first()
        payment = Payment.objects.first()
        self.assertEqual(time_log.appointment, appointment)
        self.assertEqual(time_log.hours, Decimal("1.50"))
        self.assertEqual(payment.appointment, appointment)
        self.assertEqual(payment.amount, Decimal("200.00"))
        self.assertEqual(payment.status, "pending")

    def test_completed_appointment_requires_end_time(self):
        response = self.http.post(reverse("add_appointment", args=[self.client_obj.id]), {
            "title": "Strategy Session",
            "date": "2026-07-15",
            "start_time": "09:00",
            "end_time": "",
            "price": "200.00",
            "status": "completed",
            "notes": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add an end time")
        self.assertEqual(Appointment.objects.count(), 0)

    def test_add_appointment_rejects_other_users_client(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Corp")

        response = self.http.post(reverse("add_appointment", args=[other_client.id]), {
            "title": "Consultation",
            "date": "2026-07-15",
            "start_time": "09:00",
            "end_time": "",
            "price": "150.00",
            "status": "upcoming",
            "notes": "",
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_edit_appointment_post_updates_appointment(self):
        appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
            status="upcoming",
        )

        response = self.http.post(reverse("edit_appointment", args=[appointment.id]), {
            "title": "Updated Consultation",
            "date": "2026-07-16",
            "start_time": "10:00",
            "end_time": "",
            "price": "175.00",
            "status": "rescheduled",
            "notes": "Moved by client",
        })

        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.title, "Updated Consultation")
        self.assertEqual(appointment.date, date(2026, 7, 16))
        self.assertEqual(appointment.price, Decimal("175.00"))
        self.assertEqual(appointment.status, "rescheduled")

    def test_delete_appointment_post(self):
        appointment = Appointment.objects.create(
            client=self.client_obj,
            owner=self.user,
            title="Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )

        response = self.http.post(reverse("delete_appointment", args=[appointment.id]))

        self.assertRedirects(response, reverse("client_detail", args=[self.client_obj.id]))
        self.assertEqual(Appointment.objects.count(), 0)

    def test_edit_appointment_rejects_other_users_appointment(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Corp")
        appointment = Appointment.objects.create(
            client=other_client,
            owner=self.other_user,
            title="Private Consultation",
            date=date(2026, 7, 15),
            start_time=time(9, 0),
        )

        response = self.http.post(reverse("edit_appointment", args=[appointment.id]), {
            "title": "Changed",
            "date": "2026-07-16",
            "start_time": "10:00",
            "end_time": "",
            "price": "999.00",
            "status": "upcoming",
            "notes": "",
        })

        self.assertEqual(response.status_code, 404)
