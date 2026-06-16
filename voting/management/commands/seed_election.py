from django.core.management.base import BaseCommand
from django.utils import timezone

from voting.models import Candidate
from voting.models import Election
from voting.models import Position


SEED_DATA = [
    {
        "position": "School President",
        "icon": "👑",
        "candidates": [
            {"name": "Arjun Mehta", "class_name": "Class 10-A", "motto": "Leading with vision, serving with heart.", "photo": "voting/photos/m1.png"},
            {"name": "Priya Sharma", "class_name": "Class 10-B", "motto": "Together we rise, divided we fall.", "photo": "voting/photos/f1.png"},
            {"name": "Rahul Nair", "class_name": "Class 10-C", "motto": "Your voice, my mission.", "photo": "voting/photos/m2.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
    {
        "position": "Vice President",
        "icon": "🌟",
        "candidates": [
            {"name": "Sneha Patel", "class_name": "Class 9-A", "motto": "Empowering every student every day.", "photo": "voting/photos/f2.png"},
            {"name": "Kiran Das", "class_name": "Class 9-B", "motto": "Dedication, integrity, excellence.", "photo": "voting/photos/m3.png"},
            {"name": "Aisha Khan", "class_name": "Class 9-C", "motto": "Stronger together, brighter tomorrow.", "photo": "voting/photos/f3.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
    {
        "position": "General Secretary",
        "icon": "📋",
        "candidates": [
            {"name": "Dev Pillai", "class_name": "Class 9-A", "motto": "Organised, efficient, always ready.", "photo": "voting/photos/m4.png"},
            {"name": "Meera Joshi", "class_name": "Class 9-B", "motto": "Your needs, my responsibility.", "photo": "voting/photos/f4.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
    {
        "position": "Treasurer",
        "icon": "💰",
        "candidates": [
            {"name": "Rohan Verma", "class_name": "Class 8-A", "motto": "Every rupee counts, every student matters.", "photo": "voting/photos/m1.png"},
            {"name": "Fatima Zahra", "class_name": "Class 8-B", "motto": "Transparent, fair and accountable.", "photo": "voting/photos/f1.png"},
            {"name": "Nikhil Gupta", "class_name": "Class 8-C", "motto": "Smart spending for a better school.", "photo": "voting/photos/m2.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
    {
        "position": "Sports Captain",
        "icon": "🏆",
        "candidates": [
            {"name": "Ayesha Reddy", "class_name": "Class 10-A", "motto": "Team spirit fuels every victory.", "photo": "voting/photos/f2.png"},
            {"name": "Samir Bose", "class_name": "Class 10-B", "motto": "Play hard, win together, stand united.", "photo": "voting/photos/m3.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
    {
        "position": "Cultural Secretary",
        "icon": "🎭",
        "candidates": [
            {"name": "Tanvi Iyer", "class_name": "Class 9-C", "motto": "Art, culture & creativity for all.", "photo": "voting/photos/f3.png"},
            {"name": "Zara Ahmed", "class_name": "Class 9-A", "motto": "Celebrate diversity, inspire creativity.", "photo": "voting/photos/f4.png"},
            {"name": "Ishaan Roy", "class_name": "Class 9-B", "motto": "Every talent deserves a stage.", "photo": "voting/photos/m4.png"},
            {"name": "NOTA", "class_name": "None of the above.", "motto": "None of the above.", "photo": "", "is_nota": True},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a sample school election with positions and candidates."

    def add_arguments(self, parser):
        parser.add_argument("--title", default="Student Council Election 2026-27")
        parser.add_argument("--school", default="Mices Public School")

    def handle(self, *args, **options):
        election = Election.objects.create(
            title=options["title"],
            school_name=options["school"],
            status=Election.STATUS_OPEN,
            starts_at=timezone.now(),
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
                    order=c_index,
                    is_nota=candidate_data.get("is_nota", False),
                )

        self.stdout.write(self.style.SUCCESS(f"Seeded election: {election.title}"))
