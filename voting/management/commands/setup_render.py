import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from voting.models import Election
from voting.management.commands.seed_election import Command as SeedElectionCommand

class Command(BaseCommand):
    help = "Runs initial database setup for Render: creates default users and seeds sample data if empty."

    def handle(self, *args, **options):
        User = get_user_model()

        # Admin superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(username="admin", password="adminpassword123")
            self.stdout.write(self.style.SUCCESS("Created superuser: admin"))
        else:
            user = User.objects.get(username="admin")
            user.set_password("adminpassword123")
            user.save()
            self.stdout.write("Updated password for user: admin")

        # Invigilator user
        if not User.objects.filter(username="invigilator").exists():
            User.objects.create_user(username="invigilator", password="MicesInvigilator2026", is_staff=False, is_superuser=False)
            self.stdout.write(self.style.SUCCESS("Created user: invigilator"))
        else:
            user = User.objects.get(username="invigilator")
            user.set_password("MicesInvigilator2026")
            user.save()
            self.stdout.write("Updated password for user: invigilator")

        # Test user
        if not User.objects.filter(username="testuser").exists():
            User.objects.create_user(username="testuser", password="MicesTest2026", is_staff=False, is_superuser=False)
            self.stdout.write(self.style.SUCCESS("Created user: testuser"))
        else:
            user = User.objects.get(username="testuser")
            user.set_password("MicesTest2026")
            user.save()
            self.stdout.write("Updated password for user: testuser")

        # micestest user
        if not User.objects.filter(username="micestest").exists():
            User.objects.create_user(username="micestest", password="MicesTest2026", is_staff=False, is_superuser=False)
            self.stdout.write(self.style.SUCCESS("Created user: micestest"))
        else:
            user = User.objects.get(username="micestest")
            user.set_password("MicesTest2026")
            user.save()
            self.stdout.write("Updated password for user: micestest")

        # Seed election if database is empty
        if Election.objects.count() == 0:
            self.stdout.write("No elections found. Seeding sample election data...")
            seed_cmd = SeedElectionCommand()
            # Call seed command handler directly
            seed_cmd.handle(title="Student Council Election 2026-27", school="Mices Public School")
            self.stdout.write(self.style.SUCCESS("Sample election data seeded successfully."))
        else:
            self.stdout.write("Elections exist in the database. Skipping database seeding.")
