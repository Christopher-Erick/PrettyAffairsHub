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
        self.client_user = User.objects.create_user(
            "clientuser",
            email="client@example.com",
            password="PrettyClient2026!",
        )
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

    def test_login_redirects_to_shop(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "client@example.com", "password": "PrettyClient2026!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("catalog:shop"))

    def test_client_cannot_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "clientuser", "password": "PrettyClient2026!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please sign in with your email address.")

    def test_admin_logs_in_with_username_not_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "adminuser", "password": "PrettyAdmin2026!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("catalog:shop"))

        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "admin@example.com", "password": "PrettyAdmin2026!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Staff accounts")
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ClientSessionPolicyTests(TestCase):
    def setUp(self):
        Group.objects.get_or_create(name=CLIENTS_GROUP)
        Group.objects.get_or_create(name=ADMINS_GROUP)
        self.client_user = User.objects.create_user(
            "shopper",
            email="shopper@example.com",
            password="PrettyClient2026!",
        )
        self.client_user.groups.add(Group.objects.get(name=CLIENTS_GROUP))
        self.admin_user = User.objects.create_superuser(
            "deskadmin", "desk@example.com", "PrettyAdmin2026!"
        )
        assign_admin_role(self.admin_user, superuser=True)

    def test_second_client_login_signs_out_earlier_device(self):
        first = Client()
        second = Client()
        self.assertTrue(first.login(username="shopper", password="PrettyClient2026!"))
        self.assertEqual(first.get(reverse("accounts:profile")).status_code, 200)

        self.assertTrue(second.login(username="shopper", password="PrettyClient2026!"))
        self.assertEqual(second.get(reverse("accounts:profile")).status_code, 200)

        kicked = first.get(reverse("accounts:profile"))
        self.assertEqual(kicked.status_code, 302)
        self.assertIn(reverse("accounts:login"), kicked.url)

    def test_admin_may_stay_signed_in_on_two_devices(self):
        first = Client()
        second = Client()
        self.assertTrue(first.login(username="deskadmin", password="PrettyAdmin2026!"))
        self.assertTrue(second.login(username="deskadmin", password="PrettyAdmin2026!"))
        self.assertEqual(first.get(reverse("accounts:profile")).status_code, 200)
        self.assertEqual(second.get(reverse("accounts:profile")).status_code, 200)

    def test_client_idle_timeout_signs_out(self):
        import time

        from django.test import override_settings

        with override_settings(CLIENT_IDLE_TIMEOUT_SECONDS=30):
            self.assertTrue(self.client.login(username="shopper", password="PrettyClient2026!"))
            session = self.client.session
            session["client_last_activity"] = time.time() - 120
            session.save()
            response = self.client.get(reverse("accounts:profile"))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_admin_ignores_idle_timeout(self):
        import time

        from django.test import override_settings

        with override_settings(CLIENT_IDLE_TIMEOUT_SECONDS=30):
            self.assertTrue(self.client.login(username="deskadmin", password="PrettyAdmin2026!"))
            session = self.client.session
            session["client_last_activity"] = time.time() - 120
            session.save()
            response = self.client.get(reverse("accounts:profile"))
            self.assertEqual(response.status_code, 200)
