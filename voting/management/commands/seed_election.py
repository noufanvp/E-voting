from django.core.management.base import BaseCommand
from django.utils import timezone

from voting.models import Candidate
from voting.models import Election
from voting.models import Position


SEED_DATA = [
    {
        "position": "HEAD BOY",
        "icon": "👑",
        "candidates": [
            {"name": "Muhammed Aiman Changana", "class_name": "N/A", "motto": "", "photo": "voting/photos/Muhammed_Aiman_Changana.jpg", "symbol": "voting/symbols/symbol_globe.png"},
            {"name": "Aman Muhammed", "class_name": "N/A", "motto": "", "photo": "voting/photos/Aman_Muhammed.jpg", "symbol": "voting/symbols/symbol_car.png"},
            {"name": "Muhammed Ayaan KT", "class_name": "N/A", "motto": "", "photo": "voting/photos/Muhammed_Ayaan_KT.jpg", "symbol": "voting/symbols/symbol_tree.png"},
        ],
    },
    {
        "position": "SPORTS CAPTAIN",
        "icon": "🌟",
        "candidates": [
            {"name": "Muhammed Hadi MP", "class_name": "N/A", "motto": "", "photo": "voting/photos/Muhammed_Hadi_MP.jpg", "symbol": "voting/symbols/symbol_cricketBatAndBall.png"},
            {"name": "Shahazin U", "class_name": "N/A", "motto": "", "photo": "voting/photos/Shahazin_U.jpg", "symbol": "voting/symbols/symbol_football.png"},
        ],
    },
    {
        "position": "FINE ARTS SECRETARY",
        "icon": "🎨",
        "candidates": [
            {"name": "Shada Fathima", "class_name": "N/A", "motto": "", "photo": "voting/photos/Shada_Fathima.jpg", "symbol": "voting/symbols/symbol_camera.png"},
            {"name": "Fathima Hadiya M", "class_name": "N/A", "motto": "", "photo": "voting/photos/Fathima_Hadiya_M.jpg", "symbol": "voting/symbols/symbol_torch.png"},
            {"name": "Ehan Muhammed TK", "class_name": "N/A", "motto": "", "photo": "voting/photos/Ehan_Muhammed_TK.jpg", "symbol": "voting/symbols/symbol_autorickshaw.png"},
            {"name": "Naban M", "class_name": "N/A", "motto": "", "photo": "voting/photos/Naban_M.jpg", "symbol": "voting/symbols/symbol_jeep.png"}
        ],
    },
    {
        "position": "MAGAZINE EDITOR",
        "icon": "📚",
        "candidates": [
            {"name": "Gayathri P", "class_name": "N/A", "motto": "", "photo": "voting/photos/Gayathiri_P.jpg", "symbol": "voting/symbols/symbol_guitar.png"},
            {"name": "Abdullah Nihal N", "class_name": "N/A", "motto": "", "photo": "voting/photos/Abdullah_Nihal_N.jpg", "symbol": "voting/symbols/symbol_laptop.png"},
            {"name": "Navaru Rahman", "class_name": "N/A", "motto": "", "photo": "voting/photos/Navaru_Rahman.jpg", "symbol": "voting/symbols/symbol_pen.png"},
            {"name": "Raiza Aysha MP", "class_name": "N/A", "motto": "", "photo": "voting/photos/Raiza_Aysha_P.jpg", "symbol": "voting/symbols/symbol_star.png"},
            {"name": "Azim Sadath P", "class_name": "N/A", "motto": "", "photo": "voting/photos/Azim_Sadath_P.jpg", "symbol": "voting/symbols/symbol_bicycle.png"}            
        ],
    },
    {
        "position": "HEAD PREFECT",
        "icon": "🏆",
        "candidates": [
            {"name": "Sheza Fathima K", "class_name": "N/A", "motto": "", "photo": "voting/photos/Sheza_Fathima_K.jpg", "symbol": "voting/symbols/symbol_bulb.png"},
            {"name": "Muhammed Yusuf", "class_name": "N/A", "motto": "", "photo": "voting/photos/Muhammed_Yusuf.jpg", "symbol": "voting/symbols/symbol_bugle.png"},
            {"name": "Haya Binth Shahrath", "class_name": "N/A", "motto": "", "photo": "voting/photos/Haya_Binth_Shahrath.jpg", "symbol": "voting/symbols/symbol_pencil.png"},
            {"name": "Dhaheen MP", "class_name": "N/A", "motto": "", "photo": "voting/photos/Dhaheen_MP.jpg", "symbol": "voting/symbols/symbol_clock.png"}            
        ],
    }
]


class Command(BaseCommand):
    help = "Seed a sample school election with positions and candidates."

    def add_arguments(self, parser):
        parser.add_argument("--title", default="Student Council Election 2026-27")
        parser.add_argument("--school", default="Mices Public School")

    def handle(self, *args, **options):
        # Create default users if they don't exist
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Admin superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(username="admin", password="admin123")
            self.stdout.write("Created superuser: admin")
        else:
            user = User.objects.get(username="admin")
            user.set_password("admin123")
            user.save()
            self.stdout.write("Updated password for user: admin")

        # Invigilator user
        if not User.objects.filter(username="invigilator").exists():
            User.objects.create_user(username="invigilator", password="MicesInvigilator2026", is_staff=False, is_superuser=False)
            self.stdout.write("Created user: invigilator")
        else:
            user = User.objects.get(username="invigilator")
            user.set_password("MicesInvigilator2026")
            user.save()
            self.stdout.write("Updated password for user: invigilator")

        # Test user
        if not User.objects.filter(username="testuser").exists():
            User.objects.create_user(username="testuser", password="MicesTest2026", is_staff=False, is_superuser=False)
            self.stdout.write("Created user: testuser")
        else:
            user = User.objects.get(username="testuser")
            user.set_password("MicesTest2026")
            user.save()
            self.stdout.write("Updated password for user: testuser")

        # micestest user
        if not User.objects.filter(username="micestest").exists():
            User.objects.create_user(username="micestest", password="MicesTest2026", is_staff=False, is_superuser=False)
            self.stdout.write("Created user: micestest")
        else:
            user = User.objects.get(username="micestest")
            user.set_password("MicesTest2026")
            user.save()
            self.stdout.write("Updated password for user: micestest")

        # Clean previous data to ensure a fresh, active seed
        from datetime import timedelta
        from voting.models import Vote, Ballot
        Vote.objects.all().delete()
        Ballot.objects.all().delete()
        Election.objects.all().delete()

        election = Election.objects.create(
            title=options["title"],
            school_name=options["school"],
            status=Election.STATUS_OPEN,
            starts_at=timezone.now() - timedelta(hours=2),
        )

        for p_index, position_data in enumerate(SEED_DATA):
            position = Position.objects.create(
                election=election,
                name=position_data["position"],
                icon=position_data["icon"],
                order=p_index,
            )
            for c_index, candidate_data in enumerate(position_data["candidates"]):
                Candidate.objects.create(
                    position=position,
                    name=candidate_data["name"],
                    class_name=candidate_data.get("class_name", ""),
                    motto=candidate_data.get("motto", ""),
                    photo=candidate_data.get("photo", ""),
                    symbol=candidate_data.get("symbol", ""),
                    order=c_index,
                    is_nota=candidate_data.get("is_nota", False),
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded election: {election.title}"))
