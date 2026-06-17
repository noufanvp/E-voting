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
            User.objects.create_superuser(username="admin", password="admin123")
            self.stdout.write(self.style.SUCCESS("Created superuser: admin"))
        else:
            user = User.objects.get(username="admin")
            user.set_password("admin123")
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

        # Seed election if the correct Mices election or its positions do not exist, or if forced
        desired_title = "Student Council Election 2026-27"
        desired_school = "Mices Public School"
        force_seed = os.environ.get("FORCE_SEED", "False") == "True"

        has_latest = Election.objects.filter(title=desired_title, school_name=desired_school).exists()
        has_positions = False
        has_legacy_formats = False

        if has_latest:
            election = Election.objects.get(title=desired_title, school_name=desired_school)
            has_positions = election.positions.exists()
            from voting.models import Candidate
            # Detect if existing data uses old extensions
            has_legacy_formats = (
                Candidate.objects.filter(photo__endswith='.jpg').exists() or
                Candidate.objects.filter(photo__endswith='.png').exists() or
                Candidate.objects.filter(symbol__endswith='.jpg').exists() or
                Candidate.objects.filter(symbol__endswith='.png').exists()
            )

        if force_seed or not has_latest or not has_positions or has_legacy_formats:
            self.stdout.write(f"Seeding election data (force_seed={force_seed}, has_latest={has_latest}, has_positions={has_positions}, has_legacy_formats={has_legacy_formats})...")
            seed_cmd = SeedElectionCommand()
            # Call seed command handler directly
            seed_cmd.handle(title=desired_title, school=desired_school)
            self.stdout.write(self.style.SUCCESS("Mices Public School election data seeded successfully."))
        else:
            self.stdout.write("Mices Public School election data already exists. Skipping database seeding.")
