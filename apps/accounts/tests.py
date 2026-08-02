from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.forms import RegisterForm
from apps.accounts.roles import ADMINS_GROUP, CLIENTS_GROUP, assign_admin_role, is_store_admin


class RoleModelTests(TestCase):
    def test_registration_assigns_clients_group(self):
        form = RegisterForm(
            data={
                "username": "client1",
                "email": "client1@example.com",
                "password1": "PrettyClient2026!",
                "password2": "PrettyClient2026!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertFalse(user.is_staff)
        self.assertTrue(user.groups.filter(name=CLIENTS_GROUP).exists())
        self.assertFalse(user.groups.filter(name=ADMINS_GROUP).exists())
        self.assertFalse(is_store_admin(user))

    def test_admin_role_flags_staff(self):
        user = User.objects.create_user("shopadmin", password="PrettyAdmin2026!")
        assign_admin_role(user)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.groups.filter(name=ADMINS_GROUP).exists())
        self.assertTrue(is_store_admin(user))


class AccountAccessTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=CLIENTS_GROUP)
        Group.objects.get_or_create(name=ADMINS_GROUP)
        self.client_user = User.objects.create_user("clientuser", password="PrettyClient2026!")
        self.client_user.groups.add(Group.objects.get(name=CLIENTS_GROUP))
        self.admin_user = User.objects.create_superuser(
            "adminuser", "admin@example.com", "PrettyAdmin2026!"
        )
        assign_admin_role(self.admin_user, superuser=True)

    def test_anonymous_has_no_admin_in_header(self):
        response = self.client.get(reverse("content:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Admin</a>")
        self.assertNotContains(response, "Store admin")

    def test_client_profile_hides_store_admin(self):
        self.client.login(username="clientuser", password="PrettyClient2026!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Store admin")
        self.assertNotContains(response, reverse("desk:home"))

    def test_admin_profile_shows_store_manager(self):
        self.client.login(username="adminuser", password="PrettyAdmin2026!")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Store Manager")
        self.assertContains(response, reverse("desk:home"))

    def test_admin_route_still_protected(self):
        anon = Client()
        response = anon.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.url)

        self.client.login(username="clientuser", password="PrettyClient2026!")
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, (302, 403))

        self.client.login(username="adminuser", password="PrettyAdmin2026!")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_login_shows_forgot_password(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forgot password?")
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_password_reset_skips_admin_accounts(self):
        from apps.accounts.forms import StyledPasswordResetForm

        self.client_user.email = "client@example.com"
        self.client_user.save(update_fields=["email"])
        self.admin_user.email = "admin@example.com"
        self.admin_user.save(update_fields=["email"])

        admin_form = StyledPasswordResetForm(data={"email": "admin@example.com"})
        self.assertTrue(admin_form.is_valid())
        self.assertEqual(list(admin_form.get_users("admin@example.com")), [])

        client_form = StyledPasswordResetForm(data={"email": "client@example.com"})
        self.assertTrue(client_form.is_valid())
        users = list(client_form.get_users("client@example.com"))
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].pk, self.client_user.pk)

    def test_login_redirects_to_account(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "clientuser", "password": "PrettyClient2026!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:profile"))
