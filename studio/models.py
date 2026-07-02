from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


# ---------- Practices ----------

class Practice(models.Model):
    """A type of yoga practice (Vinyasa, Yin, Restorative, Breathwork)."""

    PRACTICE_TAGS = [
        ("movement", "Movement"),
        ("stillness", "Stillness"),
        ("rest", "Rest"),
        ("breath", "Breath"),
    ]

    slug = models.SlugField(unique=True, max_length=60)
    name = models.CharField(max_length=80)
    tag = models.CharField(max_length=20, choices=PRACTICE_TAGS)
    tagline = models.CharField(max_length=120, blank=True)
    description = models.TextField()
    typical_duration_minutes = models.PositiveIntegerField(default=60)
    intensity = models.PositiveSmallIntegerField(default=3, help_text="1–5")
    default_room = models.ForeignKey(
        "StudioRoom", on_delete=models.SET_NULL, null=True, blank=True, related_name="practices"
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ---------- Rooms ----------

class StudioRoom(models.Model):
    """A physical room in the studio (Garden, Sun)."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    capacity = models.PositiveSmallIntegerField(default=settings.STUDIO_MAX_CLASS_SIZE)
    has_natural_light = models.BooleanField(default=True)
    is_skylit = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------- Teachers ----------

class Teacher(models.Model):
    """A yoga teacher at the studio."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80, help_text="e.g. 'Vinyasa · 14 years'")
    discipline = models.CharField(max_length=80, help_text="e.g. 'Slow flow, breath-led'")
    why_i_teach = models.TextField(help_text="Personal statement shown on hover")
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="teachers/", blank=True)
    photo_url = models.URLField(blank=True, help_text="External image if no upload")
    practices = models.ManyToManyField(Practice, blank=True, related_name="teachers")
    years_teaching = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ---------- Weekly class template ----------

WEEKDAYS = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]


class YogaClass(models.Model):
    """
    A recurring weekly class.

    The schedule is templated by day_of_week + start_time, and the API
    materialises concrete sessions for any given date on demand.
    """

    practice = models.ForeignKey(Practice, on_delete=models.PROTECT, related_name="classes")
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name="classes")
    room = models.ForeignKey(StudioRoom, on_delete=models.PROTECT, related_name="classes")

    day_of_week = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60)

    # Overrides the room capacity if needed
    capacity_override = models.PositiveSmallIntegerField(null=True, blank=True)

    subtitle = models.CharField(max_length=120, blank=True, help_text="e.g. 'Slow Flow'")
    description_override = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["day_of_week", "start_time", "room"],
                name="unique_weekly_slot_per_room",
            ),
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time:%H:%M} — {self.practice.name}"

    @property
    def effective_capacity(self):
        return self.capacity_override or self.room.capacity

    def end_time(self):
        from datetime import datetime
        d = datetime.combine(timezone.now().date(), self.start_time)
        return (d + timedelta(minutes=self.duration_minutes)).time()


# ---------- Bookings ----------

class Booking(models.Model):
    """A student's reservation for a specific class on a specific date."""

    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("waitlist", "Waitlist"),
        ("cancelled", "Cancelled"),
        ("noshow", "No-show"),
    ]

    yoga_class = models.ForeignKey(YogaClass, on_delete=models.PROTECT, related_name="bookings")
    session_date = models.DateField(help_text="The concrete date of the class")

    student_name = models.CharField(max_length=160)
    student_email = models.EmailField()
    student_phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    is_first_class = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="confirmed")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-session_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["yoga_class", "session_date", "student_email"],
                condition=~models.Q(status="cancelled"),
                name="unique_active_booking_per_email_per_session",
            ),
        ]
        indexes = [
            models.Index(fields=["session_date", "status"]),
            models.Index(fields=["yoga_class", "session_date"]),
        ]

    def __str__(self):
        return f"{self.student_name} — {self.yoga_class} on {self.session_date}"

    def clean(self):
        if self.yoga_class and self.session_date:
            if self.session_date.weekday() != self.yoga_class.day_of_week:
                raise ValidationError(
                    {"session_date": "Session date weekday does not match the class's day_of_week."}
                )
        if self.status == "confirmed":
            confirmed_count = Booking.objects.filter(
                yoga_class=self.yoga_class,
                session_date=self.session_date,
                status="confirmed",
            ).exclude(pk=self.pk).count()
            if confirmed_count >= self.yoga_class.effective_capacity:
                raise ValidationError(
                    {"status": "Class is full — please set this booking to waitlist."}
                )


# ---------- First-class-free form submissions ----------

class FreeClassRequest(models.Model):
    """The lead-capture form on the landing page."""

    PRACTICE_CHOICES = [
        ("vinyasa", "Vinyasa — slow flow"),
        ("yin", "Yin — long holds"),
        ("restorative", "Restorative — fully supported"),
        ("breathwork", "Breathwork — seated"),
        ("unsure", "Not sure yet"),
    ]

    TIME_CHOICES = [
        ("weekday-am", "Weekday mornings"),
        ("weekday-pm", "Weekday evenings"),
        ("weekend", "Weekends"),
        ("any", "Anytime"),
    ]

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("booked", "Booked"),
        ("closed", "Closed"),
    ]

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True, help_text="Phone number")  # <-- MAKE SURE THIS LINE EXISTS
    preferred_practice = models.CharField(max_length=20, choices=PRACTICE_CHOICES, blank=True)
    preferred_time = models.CharField(max_length=20, choices=TIME_CHOICES, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="new")
    internal_notes = models.TextField(blank=True, help_text="Staff-only notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.email}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

# ---------- Studio info (singleton-ish settings) ----------

class StudioInfo(models.Model):
    """Editable studio-wide info shown across the site."""

    name = models.CharField(max_length=120, default="Stillpoint")
    tagline = models.CharField(max_length=200, blank=True)
    address_line_1 = models.CharField(max_length=200, default="147 Almond Street")
    address_line_2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80, default="Oakland")
    state = models.CharField(max_length=40, default="CA")
    postal_code = models.CharField(max_length=20, default="94610")
    phone = models.CharField(max_length=40, default="(510) 555-0147")
    email = models.EmailField(default="hello@stillpoint.studio")
    hours = models.CharField(max_length=120, default="Open daily · 6:30am – 8:30pm")
    founded_year = models.PositiveSmallIntegerField(default=2014)

    class Meta:
        verbose_name = "Studio info"
        verbose_name_plural = "Studio info"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce singleton
        if not self.pk and StudioInfo.objects.exists():
            existing = StudioInfo.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)