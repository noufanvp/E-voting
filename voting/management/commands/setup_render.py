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

        # Seeding logic: only seed if database contains NO elections at all (meaning it's a completely fresh deploy),
        # or if FORCE_SEED is explicitly requested. This prevents wiping the database and deleting user-created
        # elections, positions, and votes on subsequent redeployments.
        desired_title = "Student Council Election 2026-27"
        desired_school = "Mices Public School"
        has_any_election = Election.objects.exists()
        force_seed = os.environ.get("FORCE_SEED", "False") == "True"

        # Check details for the default election only if it exists
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

        # Seeding should run only if forced, if the DB is empty, or if we have the default election in an incomplete/outdated state
        should_seed = force_seed or (not has_any_election) or (has_latest and (not has_positions or has_legacy_formats))

        if should_seed:
            self.stdout.write(f"Seeding election data (force_seed={force_seed}, has_any_election={has_any_election}, has_positions={has_positions}, has_legacy_formats={has_legacy_formats})...")
            seed_cmd = SeedElectionCommand()
            # Seed Mices Public School
            seed_cmd.handle(title="Student Council Election 2026-27", school="Mices Public School")
            self.stdout.write(self.style.SUCCESS("Mices Public School election data seeded successfully."))
            
            # Seed Narikkuni English Medium School
            seed_cmd.handle(title="Student Council Election 2026-27", school="Narikkuni English Medium School")
            self.stdout.write(self.style.SUCCESS("Narikkuni English Medium School election data seeded successfully."))
        else:
            self.stdout.write("Elections already exist in the database. Skipping database seeding to preserve user data.")
