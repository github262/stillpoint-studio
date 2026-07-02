from rest_framework import serializers
from .models import (
    Practice, StudioRoom, Teacher, YogaClass, Booking, FreeClassRequest, StudioInfo
)


class StudioRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioRoom
        fields = ["id", "slug", "name", "description", "capacity",
                  "has_natural_light", "is_skylit"]


class PracticeSerializer(serializers.ModelSerializer):
    default_room = StudioRoomSerializer(read_only=True)
    tag_label = serializers.CharField(source="get_tag_display", read_only=True)

    class Meta:
        model = Practice
        fields = ["id", "slug", "name", "tag", "tag_label", "tagline",
                  "description", "typical_duration_minutes", "intensity",
                  "default_room", "order"]


class TeacherSerializer(serializers.ModelSerializer):
    practices = PracticeSerializer(many=True, read_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ["id", "slug", "name", "role", "discipline", "why_i_teach",
                  "bio", "photo", "photo_url", "years_teaching", "practices",
                  "order"]

    def get_photo(self, obj):
        if obj.photo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return obj.photo_url or ""


class YogaClassSerializer(serializers.ModelSerializer):
    practice = PracticeSerializer(read_only=True)
    teacher = TeacherSerializer(read_only=True)
    room = StudioRoomSerializer(read_only=True)
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)
    end_time = serializers.TimeField(read_only=True)
    effective_capacity = serializers.IntegerField(read_only=True)

    class Meta:
        model = YogaClass
        fields = ["id", "practice", "teacher", "room", "day_of_week", "day_name",
                  "start_time", "end_time", "duration_minutes", "effective_capacity",
                  "subtitle", "description_override", "is_active"]


class ScheduleRowSerializer(serializers.ModelSerializer):
    """
    Adds seat availability computed for a specific session date.
    The view passes `session_date` through context.
    """
    practice = PracticeSerializer(read_only=True)
    teacher = TeacherSerializer(read_only=True)
    room = StudioRoomSerializer(read_only=True)
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)
    end_time = serializers.TimeField(read_only=True)
    effective_capacity = serializers.IntegerField(read_only=True)
    session_date = serializers.DateField(read_only=True)
    seats_taken = serializers.IntegerField(read_only=True)
    seats_available = serializers.IntegerField(read_only=True)
    seat_status = serializers.CharField(read_only=True)  # open | few | full

    class Meta:
        model = YogaClass
        fields = ["id", "practice", "teacher", "room", "day_of_week", "day_name",
                  "session_date", "start_time", "end_time", "duration_minutes",
                  "effective_capacity", "seats_taken", "seats_available",
                  "seat_status", "subtitle", "description_override", "is_active"]


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["yoga_class", "session_date", "student_name", "student_email",
                  "student_phone", "notes", "is_first_class"]

    def validate(self, attrs):
        yc = attrs["yoga_class"]
        date = attrs["session_date"]
        if date.weekday() != yc.day_of_week:
            raise serializers.ValidationError(
                {"session_date": "Selected date does not match the class's weekday."}
            )
        if date < timezone_now().date():
            raise serializers.ValidationError(
                {"session_date": "Cannot book a class in the past."}
            )
        # Duplicate check
        existing = Booking.objects.filter(
            yoga_class=yc, session_date=date,
            student_email__iexact=attrs["student_email"],
        ).exclude(status="cancelled").exists()
        if existing:
            raise serializers.ValidationError(
                "You already have an active booking for this class."
            )
        # Capacity check
        confirmed = Booking.objects.filter(
            yoga_class=yc, session_date=date, status="confirmed"
        ).count()
        if confirmed >= yc.effective_capacity:
            attrs["status"] = "waitlist"
        else:
            attrs["status"] = "confirmed"
        return attrs


class FreeClassRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreeClassRequest
        fields = ["id", "first_name", "last_name", "email", "phone", "preferred_practice", "preferred_time", "notes", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_email(self, value):
        # Block duplicate submissions within 24h
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)
        if FreeClassRequest.objects.filter(email__iexact=value, created_at__gte=cutoff).exists():
            raise serializers.ValidationError(
                "We already received a request from you in the last 24 hours."
            )
        return value


class StudioInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioInfo
        fields = "__all__"


# Avoid importing timezone at module load in an odd spot
from django.utils import timezone as _tz
def timezone_now():
    return _tz.now()