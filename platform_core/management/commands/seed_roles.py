from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Administrator": {"add", "change", "delete", "view"},
    "Command Center Operator": {"add", "change", "view"},
    "Commander": {"view"},
    "Intelligence Analyst": {"view"},
    "Auditor": {"view"},
}


class Command(BaseCommand):
    help = "Create baseline operational groups using Django model permissions."

    def handle(self, *args, **options):
        incident_permissions = Permission.objects.filter(content_type__app_label="incidents")
        for role, actions in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            selected = [permission for permission in incident_permissions if permission.codename.split("_", 1)[0] in actions]
            group.permissions.set(selected)
            self.stdout.write(self.style.SUCCESS(f"{role}: {len(selected)} permissions"))
