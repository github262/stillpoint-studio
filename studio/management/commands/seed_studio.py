from django.core.management.base import BaseCommand
from django.utils import timezone
from studio.models import (
    Practice, StudioRoom, Teacher, YogaClass, StudioInfo,
)


class Command(BaseCommand):
    help = "Seed the studio database with the demo data from the landing page."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Stillpoint studio..."))

        # ---- Studio info ----
        StudioInfo.objects.update_or_create(
            pk=1,
            defaults={
                "name": "Stillpoint",
                "tagline": "A boutique yoga studio rooted in Oakland since 2014.",
                "address_line_1": "147 Almond Street",
                "city": "Oakland",
                "state": "CA",
                "postal_code": "94610",
                "phone": "(510) 555-0147",
                "email": "hello@stillpoint.studio",
                "hours": "Open daily · 6:30am – 8:30pm",
                "founded_year": 2014,
            },
        )

        # ---- Rooms ----
        garden, _ = StudioRoom.objects.get_or_create(
            slug="garden",
            defaults={
                "name": "Garden Room",
                "description": "East-facing windows, plants in every corner. Our largest room.",
                "capacity": 12,
                "has_natural_light": True,
                "is_skylit": False,
            },
        )
        sun, _ = StudioRoom.objects.get_or_create(
            slug="sun",
            defaults={
                "name": "Sun Room",
                "description": "Skylit, cushioned floor, intimate. Used for smaller practices.",
                "capacity": 8,
                "has_natural_light": True,
                "is_skylit": True,
            },
        )

        # ---- Practices ----
        vinyasa, _ = Practice.objects.update_or_create(
            slug="vinyasa",
            defaults={
                "name": "Vinyasa",
                "tag": "movement",
                "tagline": "Flow, with the breath as guide.",
                "description": (
                    "A slow, intelligent sequence that links movement to breath. "
                    "We move through sun salutations and standing postures with the "
                    "curiosity of a beginner — never the urgency of a workout."
                ),
                "typical_duration_minutes": 60,
                "intensity": 4,
                "default_room": garden,
                "order": 1,
            },
        )
        yin, _ = Practice.objects.update_or_create(
            slug="yin",
            defaults={
                "name": "Yin",
                "tag": "stillness",
                "tagline": "Long holds, deep tissue, patient attention.",
                "description": (
                    "Floor-based postures held for three to five minutes, releasing the "
                    "deeper connective tissue. A meditative practice that asks not for "
                    "effort, but for willingness to remain."
                ),
                "typical_duration_minutes": 75,
                "intensity": 2,
                "default_room": sun,
                "order": 2,
            },
        )
        restorative, _ = Practice.objects.update_or_create(
            slug="restorative",
            defaults={
                "name": "Restorative",
                "tag": "rest",
                "tagline": "Fully supported. The nervous system softens.",
                "description": (
                    "Six postures, twenty minutes each, supported entirely by bolsters, "
                    "blankets, and blocks. The body learns, slowly, that it is allowed "
                    "to rest — and the parasympathetic nervous system remembers its "
                    "native tongue."
                ),
                "typical_duration_minutes": 90,
                "intensity": 1,
                "default_room": garden,
                "order": 3,
            },
        )
        breathwork, _ = Practice.objects.update_or_create(
            slug="breathwork",
            defaults={
                "name": "Breathwork",
                "tag": "breath",
                "tagline": "Pranayama — the breath as bridge.",
                "description": (
                    "A seated practice of guided breathing techniques — alternate "
                    "nostril, three-part breath, and gentle retention. The breath, "
                    "observed closely, becomes a quiet door into the nervous system."
                ),
                "typical_duration_minutes": 45,
                "intensity": 2,
                "default_room": sun,
                "order": 4,
            },
        )

        # ---- Teachers ----
        maya, _ = Teacher.objects.update_or_create(
            slug="maya-okafor",
            defaults={
                "name": "Maya Okafor",
                "role": "Vinyasa · 14 years",
                "discipline": "Slow flow, breath-led",
                "why_i_teach": (
                    "I teach because the body remembers what the mind forgets. "
                    "Every class is a small act of remembering."
                ),
                "bio": "Maya trained in Mysore and has taught in Oakland since 2010.",
                "photo_url": "https://picsum.photos/seed/teacher-maya-portrait-warm/700/900.jpg",
                "years_teaching": 14,
                "order": 1,
            },
        )
        maya.practices.set([vinyasa])

        iris, _ = Teacher.objects.update_or_create(
            slug="iris-tanaka",
            defaults={
                "name": "Iris Tanaka",
                "role": "Yin · Breathwork · 11 years",
                "discipline": "Stillness, observation",
                "why_i_teach": (
                    "I teach so others may find the quiet I lost for years. "
                    "The mat is where I learned to listen again."
                ),
                "bio": "Iris studies with Sarah Powers and Paul Grilley.",
                "photo_url": "https://picsum.photos/seed/teacher-iris-portrait-natural/700/900.jpg",
                "years_teaching": 11,
                "order": 2,
            },
        )
        iris.practices.set([yin, breathwork])

        lena, _ = Teacher.objects.update_or_create(
            slug="lena-vargas",
            defaults={
                "name": "Lena Vargas",
                "role": "Restorative · 9 years",
                "discipline": "Nervous system, rest",
                "why_i_teach": (
                    "I teach because stillness is a kind of justice. "
                    "In a world that demands our rush, rest becomes resistance."
                ),
                "bio": "Lena is trained in Judith Lasater's restorative method.",
                "photo_url": "https://picsum.photos/seed/teacher-lena-portrait-soft/700/900.jpg",
                "years_teaching": 9,
                "order": 3,
            },
        )
        lena.practices.set([restorative, yin])

        # ---- Weekly classes (matches the frontend schedule) ----
        from datetime import time
        classes_to_create = [
            # Monday (0)
            (0, time(7, 0), vinyasa, maya, garden, 60, "Slow Flow"),
            (0, time(12, 0), breathwork, iris, sun, 45, "Midday Reset"),
            (0, time(18, 0), restorative, lena, garden, 90, "Evening Unwind"),
            # Tuesday (1)
            (1, time(7, 0), yin, iris, sun, 75, "Morning Slow"),
            (1, time(18, 0), vinyasa, maya, garden, 60, "Evening Flow"),
            # Wednesday (2)
            (2, time(7, 0), vinyasa, maya, garden, 60, "Sunrise Flow"),
            (2, time(12, 0), restorative, lena, sun, 75, "Midweek Reset", 8),
            (2, time(19, 30), yin, iris, garden, 75, "Wind-Down"),
            # Thursday (3)
            (3, time(7, 0), breathwork, iris, sun, 45, "Morning Practice"),
            (3, time(18, 0), vinyasa, maya, garden, 75, "Strong & Slow"),
            # Friday (4)
            (4, time(7, 0), yin, lena, sun, 75, "Morning Release"),
            (4, time(18, 0), restorative, maya, garden, 90, "Friday Unwind"),
            # Saturday (5)
            (5, time(9, 0), vinyasa, maya, garden, 75, "Weekend Flow"),
            (5, time(11, 0), breathwork, iris, sun, 60, "Saturday Stillness"),
            # Sunday (6)
            (6, time(10, 0), restorative, lena, garden, 90, "Sunday Slow"),
            (6, time(16, 0), yin, iris, sun, 75, "Sunday Evening"),
        ]

        for row in classes_to_create:
            day, start, practice, teacher, room, dur, subtitle = row[:7]
            cap_override = row[7] if len(row) > 7 else None
            YogaClass.objects.update_or_create(
                day_of_week=day,
                start_time=start,
                room=room,
                defaults={
                    "practice": practice,
                    "teacher": teacher,
                    "duration_minutes": dur,
                    "subtitle": subtitle,
                    "capacity_override": cap_override,
                    "is_active": True,
                },
            )

        # ---- Superuser (only if it doesn't exist) ----
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@stillpoint.studio",
                password="stillpoint123",
            )
            self.stdout.write(self.style.SUCCESS(
                "Created superuser: admin / stillpoint123  (change this immediately)"
            ))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("  - Practices:  %d" % Practice.objects.count())
        self.stdout.write("  - Rooms:      %d" % StudioRoom.objects.count())
        self.stdout.write("  - Teachers:   %d" % Teacher.objects.count())
        self.stdout.write("  - Classes:    %d" % YogaClass.objects.count())