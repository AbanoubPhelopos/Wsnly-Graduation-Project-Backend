from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from src.Core.Domain.Constants.Roles import Roles

class Command(BaseCommand):
    help = 'Seeds the database with a default admin user'

    def handle(self, *args, **options):
        User = get_user_model()
        email = 'admin@wslny.com'
        password = 'P@ssw0rd123'
        
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name='Admin',
                last_name='User',
                mobile_number='0000000000',
                role=Roles.ADMIN
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {email}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Admin user already exists: {email}'))
