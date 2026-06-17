import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from voting.models import Election
from voting.management.commands.seed_election import Command as SeedElectionCommand

class Command(BaseCommand):
    help = "Runs initial database setup for Render: creates a superuser and seeds sample data if empty."

    def handle(self, *args, **options):
        User = get_user_model()

        # Retrieve superuser configuration from environment variables or use safe defaults
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin123")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

        # Create superuser if it does not already exist
        if not User.objects.filter(username=username).exists():
            self.stdout.write(f"Creating superuser '{username}'...")
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            self.stdout.write(f"Superuser '{username}' already exists. Skipping creation.")

        # Seed election if database is empty
        if Election.objects.count() == 0:
            self.stdout.write("No elections found. Seeding sample election data...")
            seed_cmd = SeedElectionCommand()
            # Call seed command handler directly
            seed_cmd.handle(title="Student Council Election 2026-27", school="Mices Public School")
            self.stdout.write(self.style.SUCCESS("Sample election data seeded successfully."))
        else:
            self.stdout.write("Elections exist in the database. Skipping database seeding.")
