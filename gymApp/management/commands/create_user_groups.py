from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Create user groups with specified permissions'

    def handle(self, *args, **options):
        groups_permissions = {
            'CEO and Boss': {
                'permissions': [
                    'auth.add_user', 'auth.change_user', 'auth.delete_user', 'auth.view_user',
                    'auth.add_group', 'auth.change_group', 'auth.delete_group', 'auth.view_group',
                    'gymApp.add_membership', 'gymApp.change_membership', 'gymApp.delete_membership', 'gymApp.view_membership',
                    'class_schedule.add_booking', 'class_schedule.change_booking', 'class_schedule.delete_booking', 'class_schedule.view_booking',
                    'class_schedule.add_class', 'class_schedule.change_class', 'class_schedule.delete_class', 'class_schedule.view_class',
                    'class_schedule.add_session', 'class_schedule.change_session', 'class_schedule.delete_session', 'class_schedule.view_session',
                    'documentation.add_document', 'documentation.change_document', 'documentation.delete_document', 'documentation.view_document',
                    'gym_info.add_trainer', 'gym_info.change_trainer', 'gym_info.delete_trainer', 'gym_info.view_trainer'
                ]
            },
            'Team Members': {
                'permissions': [
                    'gymApp.view_membership',
                    'auth.view_user', 'auth.change_user',
                    'class_schedule.add_booking', 'class_schedule.change_booking', 'class_schedule.delete_booking', 'class_schedule.view_booking',
                    'class_schedule.view_class', 'class_schedule.view_session',
                    'documentation.view_document',
                    'gym_info.view_trainer'
                ]
            },
            'Trainers': {
                'permissions': [
                    'class_schedule.add_session', 'class_schedule.change_session', 'class_schedule.view_session',
                    'gymApp.view_membership',
                    'class_schedule.add_booking', 'class_schedule.change_booking', 'class_schedule.view_booking',
                    'class_schedule.view_class',
                    'gym_info.view_trainer'
                ]
            },
            'Kiosk': {
                'permissions': []  # Limited functionality handled through other access controls
            }
        }

        for group_name, permissions_info in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'Group "{group_name}" created.')
            else:
                self.stdout.write(f'Group "{group_name}" already exists.')

            for perm_name in permissions_info['permissions']:
                try:
                    app_label, codename = perm_name.split('.')
                    permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                    group.permissions.add(permission)
                    self.stdout.write(f'Permission "{perm_name}" added to group "{group_name}".')
                except Permission.DoesNotExist:
                    self.stdout.write(f'Permission "{perm_name}" does not exist.')

        self.stdout.write('User groups and permissions setup completed.')
