from django.test import TestCase, Client as HttpClient
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Client


class ClientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")

    def test_str_returns_client_name(self):
        client = Client.objects.create(owner=self.user, name="Acme Corp")

        self.assertEqual(str(client), "Acme Corp")

    def test_optional_fields_can_be_blank(self):
        client = Client.objects.create(owner=self.user, name="Acme Corp")

        self.assertEqual(client.contact, "")
        self.assertEqual(client.service_type, "")
        self.assertEqual(client.notes, "")

    def test_client_belongs_to_owner(self):
        client = Client.objects.create(owner=self.user, name="Acme Corp")

        self.assertEqual(client.owner, self.user)

class ClientViewTest(TestCase):
    def setUp(self):
        self.http = HttpClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.http.login(username="testuser", password="pass")

    def test_add_client_post_creates_client(self):
        response = self.http.post(reverse("add_client"), {
            "name": "Acme Corp",
            "contact": "hello@acme.com",
            "service_type": "Design",
            "notes": "Important client",
        })

        self.assertRedirects(response, reverse("client_list"))
        self.assertEqual(Client.objects.count(), 1)

        client = Client.objects.first()
        self.assertEqual(client.owner, self.user)
        self.assertEqual(client.name, "Acme Corp")

    def test_client_list_only_shows_logged_in_users_clients(self):
        Client.objects.create(owner=self.user, name="My Client")
        Client.objects.create(owner=self.other_user, name="Other Client")

        response = self.http.get(reverse("client_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Client")
        self.assertNotContains(response, "Other Client")

    def test_client_detail_rejects_other_users_client(self):
        other_client = Client.objects.create(owner=self.other_user, name="Other Client")

        response = self.http.get(reverse("client_detail", args=[other_client.id]))

        self.assertEqual(response.status_code, 404)
