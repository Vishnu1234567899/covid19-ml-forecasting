from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from forecasting.models import UserProfile, CovidDataset


SAMPLE_DATA = [
    ("Maharashtra", "India", 19.08, 72.88, "2020-04-01", "2020-04-08", 8, 10000, 1000, 3000, 6000),
    ("Delhi", "India", 28.71, 77.10, "2020-04-10", "2020-04-18", 8, 7000, 1000, 2000, 4000),
    ("Mumbai", "India", 19.08, 72.88, "2020-05-14", "2020-05-30", 16, 25000, 3000, 4000, 18000),
    ("Calcutta", "India", 22.57, 88.36, "2020-05-14", "2020-05-30", 16, 18000, 1000, 4000, 13000),
    ("Bangalore", "India", 12.97, 77.59, "2020-05-14", "2020-05-30", 16, 8000, 1000, 2000, 5000),
    ("Chennai", "India", 13.08, 80.27, "2020-04-22", "2020-04-30", 8, 10000, 1000, 3000, 6000),
    ("New York", "USA", 40.71, 74.01, "2020-05-14", "2020-05-30", 16, 12000, 2500, 2000, 7500),
    ("California", "USA", 36.77, 119.41, "2020-05-14", "2020-05-30", 16, 6000, 1500, 1200, 3300),
    ("Las Anges", "USA", 34.05, 118.24, "2020-05-14", "2020-05-30", 16, 5000, 300, 1200, 3500),
    ("Victoria", "Australia", -37.81, 144.96, "2020-04-22", "2020-04-30", 8, 600, 50, 300, 250),
    ("Colombia", "Canada", 49.28, -123.1, "2020-04-22", "2020-04-30", 8, 400, 100, 200, 100),
    ("New York", "USA", 40.71, 74.01, "2020-06-14", "2020-06-30", 16, 13000, 2500, 2000, 8500),
    ("California", "USA", 36.77, 119.41, "2020-06-14", "2020-06-30", 16, 16000, 1500, 1200, 13300),
    ("Maharashtra", "India", 19.08, 72.88, "2020-07-01", "2020-07-10", 10, 30000, 5000, 10000, 15000),
    ("Delhi", "India", 28.71, 77.10, "2020-07-01", "2020-07-10", 10, 20000, 3000, 8000, 9000),
]


class Command(BaseCommand):
    help = 'Creates default admin user and loads sample data'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                password='admin123',
                first_name='Server',
                email='admin@covid19.com'
            )
            UserProfile.objects.create(
                user=admin,
                mobile='9999999999',
                country='India',
                state='Telangana',
                city='Warangal',
                is_server_admin=True
            )
            self.stdout.write(self.style.SUCCESS('Admin created: username=admin password=admin123'))
        else:
            self.stdout.write(self.style.WARNING('Admin already exists.'))

        if not User.objects.filter(username='user1').exists():
            demo = User.objects.create_user(
                username='user1',
                password='user1234',
                first_name='Demo User'
            )
            UserProfile.objects.create(
                user=demo,
                mobile='9876543210',
                country='India',
                state='Karnataka',
                city='Bangalore',
                is_server_admin=False
            )
            self.stdout.write(self.style.SUCCESS('Demo user created: username=user1 password=user1234'))

        count = 0
        for row in SAMPLE_DATA:
            _, created = CovidDataset.objects.get_or_create(
                province_or_state=row[0],
                country_or_region=row[1],
                from_date=row[4],
                defaults={
                    'latitude': row[2], 'longitude': row[3],
                    'to_date': row[5], 'number_of_days': row[6],
                    'new_cases': row[7], 'death_cases': row[8],
                    'recovery_cases': row[9], 'ongoing_treatment_cases': row[10],
                }
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Loaded {count} sample records'))
        self.stdout.write(self.style.SUCCESS('Setup complete!'))
        self.stdout.write('Login at http://127.0.0.1:8000/login/')
        self.stdout.write('Admin: username=admin  password=admin123')
        self.stdout.write('User:  username=user1  password=user1234')