from django.db import migrations


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    clients, _ = Group.objects.get_or_create(name="Clients")
    admins, _ = Group.objects.get_or_create(name="Admins")

    for user in User.objects.all():
        if user.is_staff or user.is_superuser:
            user.groups.add(admins)
            user.groups.remove(clients)
        else:
            user.groups.add(clients)
            user.groups.remove(admins)


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Clients", "Admins"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]
