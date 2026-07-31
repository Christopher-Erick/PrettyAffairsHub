"""Client vs admin role helpers using Django auth Groups + is_staff."""

from django.contrib.auth.models import Group

CLIENTS_GROUP = "Clients"
ADMINS_GROUP = "Admins"


def get_or_create_role_groups():
    clients, _ = Group.objects.get_or_create(name=CLIENTS_GROUP)
    admins, _ = Group.objects.get_or_create(name=ADMINS_GROUP)
    return clients, admins


def assign_client_role(user):
    """Mark a user as a storefront client (never staff via registration)."""
    clients, admins = get_or_create_role_groups()
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["is_staff", "is_superuser"])
    user.groups.add(clients)
    user.groups.remove(admins)
    return user


def assign_admin_role(user, *, superuser=False):
    """Mark a user as store admin (staff access to /admin/)."""
    clients, admins = get_or_create_role_groups()
    user.is_staff = True
    if superuser:
        user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    user.groups.add(admins)
    user.groups.remove(clients)
    return user


def is_store_admin(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    return user.groups.filter(name=ADMINS_GROUP).exists()


def is_client(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if is_store_admin(user):
        return False
    return user.groups.filter(name=CLIENTS_GROUP).exists() or not user.is_staff
