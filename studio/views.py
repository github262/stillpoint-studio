# from django.shortcuts import render

# # Create your views here.

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from datetime import date, timedelta
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Practice, StudioRoom, Teacher, YogaClass, Booking,
    FreeClassRequest, StudioInfo,
)
from .serializers import (
    PracticeSerializer, StudioRoomSerializer, TeacherSerializer,
    YogaClassSerializer, ScheduleRowSerializer, BookingCreateSerializer,
    FreeClassRequestSerializer, StudioInfoSerializer,
)
from .permissions import IsAdminOrReadOnly


def _next_occurrence(day_of_week: int, from_date: date = None) -> date:
    """Return the next date (>= from_date, default today) matching day_of_week."""
    from_date = from_date or timezone.now().date()
    delta = (day_of_week - from_date.weekday()) % 7
    return from_date + timedelta(days=delta)


# ---------- Read-only public catalogues ----------

class PracticeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Practice.objects.filter(is_active=True).select_related("default_room")
    serializer_class = PracticeSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "tagline", "description"]
    ordering_fields = ["order", "name"]


class TeacherViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Teacher.objects.filter(is_active=True).prefetch_related("practices")
    serializer_class = TeacherSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "role", "discipline"]
    ordering_fields = ["order", "name"]


class StudioRoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StudioRoom.objects.all()
    serializer_class = StudioRoomSerializer
    permission_classes = [AllowAny]


# ---------- Schedule (the meat of the public API) ----------

class ScheduleView(APIView):
    """
    GET /api/schedule/?weeks=1
    Returns the upcoming week's classes with computed seat availability.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        weeks = int(request.query_params.get("weeks", "1"))
        weeks = max(1, min(weeks, 4))

        today = timezone.now().date()
        classes = YogaClass.objects.filter(is_active=True).select_related(
            "practice", "teacher", "room", "practice__default_room"
        ).order_by("day_of_week", "start_time")

        # Build per-day list for N weeks ahead
        rows = []
        for w in range(weeks):
            week_start = today + timedelta(weeks=w)
            for cls in classes:
                session_date = _next_occurrence(cls.day_of_week, from_date=week_start)
                if session_date < today:
                    continue
                rows.append((cls, session_date))

        rows.sort(key=lambda r: (r[1], r[0].start_time))

        # Bulk-fetch booking counts for all relevant (class, date) pairs
        confirmed_counts = {}
        waitlist_counts = {}
        if rows:
            class_ids = [c.id for c, _ in rows]
            date_set = {d for _, d in rows}
            qs = (
                Booking.objects
                .filter(yoga_class_id__in=class_ids, session_date__in=date_set)
                .values("yoga_class_id", "session_date", "status")
                .annotate(c=Count("id"))
            )
            for row in qs:
                key = (row["yoga_class_id"], row["session_date"])
                if row["status"] == "confirmed":
                    confirmed_counts[key] = row["c"]
                elif row["status"] == "waitlist":
                    waitlist_counts[key] = row["c"]

        out = []
        for cls, session_date in rows:
            key = (cls.id, session_date)
            taken = confirmed_counts.get(key, 0)
            cap = cls.effective_capacity
            available = max(0, cap - taken)
            if available == 0:
                seat_status = "full"
            elif available <= 3:
                seat_status = "few"
            else:
                seat_status = "open"

            data = ScheduleRowSerializer(cls, context={
                "request": request,
                "session_date": session_date,
            }).data
            data["session_date"] = session_date.isoformat()
            data["seats_taken"] = taken
            data["seats_available"] = available
            data["seat_status"] = seat_status
            data["waitlist_count"] = waitlist_counts.get(key, 0)
            out.append(data)

        # Group by date for easier frontend consumption
        grouped = {}
        for row in out:
            grouped.setdefault(row["session_date"], []).append(row)

        return Response({
            "week_starting": today.isoformat(),
            "weeks": weeks,
            "days": [
                {"date": d, "classes": classes}
                for d, classes in sorted(grouped.items())
            ],
        })


# ---------- Booking ----------

@method_decorator(csrf_exempt, name='dispatch')
class BookingCreateView(generics.CreateAPIView):
    """POST /api/bookings/ — public endpoint."""
    queryset = Booking.objects.all()
    serializer_class = BookingCreateSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # Prevents CSRF enforcement for public users

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        output = BookingCreateSerializer(booking).data
        output["status"] = booking.status
        output["message"] = (
            "You're on the waitlist — we'll email you if a seat opens."
            if booking.status == "waitlist"
            else "Your seat is confirmed. We'll see you soon."
        )
        return Response(output, status=status.HTTP_201_CREATED)

class BookingDetailView(generics.RetrieveAPIView):
    """Lookup by email + booking id (for the student to check their booking)."""
    permission_classes = [AllowAny]
    queryset = Booking.objects.all()
    serializer_class = BookingCreateSerializer

    def get_object(self):
        email = self.request.query_params.get("email")
        pk = self.kwargs.get("pk")
        return Booking.objects.get(pk=pk, student_email__iexact=email)


# ---------- First-class-free form ----------

@method_decorator(csrf_exempt, name='dispatch')
class FreeClassRequestView(generics.CreateAPIView):
    """POST /api/free-class/"""
    queryset = FreeClassRequest.objects.all()
    serializer_class = FreeClassRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save()
        
        # Trigger the email reply
        self.send_confirmation_email(req)
        
        return Response({
            "id": req.id,
            "message": "Thank you — we'll write to you within 24 hours to confirm your first class.",
            "status": req.status,
        }, status=status.HTTP_201_CREATED)

    def send_confirmation_email(self, req_instance):
        """Sends a beautifully formatted HTML email reply to the student."""
        subject = "Welcome to Stillpoint — We can't wait to meet you"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [req_instance.email]

        text_content = f"""
Hi {req_instance.first_name},

Thank you for reaching out to Stillpoint. We received your request for a complimentary first class.

We will look over your preferences and reach out within 24 hours to match you with the perfect teacher and time.

In the meantime, here is everything you need to know:
- We are located at 147 Almond Street, Oakland.
- Please arrive 10-15 minutes early to settle in.
- We provide all mats, props, and tea. Just wear comfortable clothing.

See you soon,
The Stillpoint Team
        """

        html_content = f"""
        <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px; background-color: #F7F2E8; color: #2E2A21; border: 1px solid #D9CFBC;">
            <h1 style="font-family: Georgia, serif; font-weight: 300; color: #4F5D43; font-size: 32px; margin-bottom: 20px;">Welcome to Stillpoint, {req_instance.first_name}.</h1>
            <p style="font-size: 16px; line-height: 1.6; color: #6F6757;">
                Thank you for reaching out. We have received your request for a complimentary first class.
            </p>
            <p style="font-size: 16px; line-height: 1.6; color: #6F6757;">
                We will look over your preferences and reach out within 24 hours to match you with the perfect teacher and time.
            </p>
            
            <div style="margin: 30px 0; padding: 20px; background-color: #FBF7EE; border-left: 3px solid #B5634A;">
                <h3 style="margin-top: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; color: #B5634A;">What to expect</h3>
                <ul style="padding-left: 20px; color: #2E2A21; font-size: 15px; line-height: 1.8;">
                    <li>Arrive 10–15 minutes early to settle in.</li>
                    <li>We provide all mats, props, and tea. Just wear comfortable clothing.</li>
                    <li>Our studio is located at 147 Almond Street, Oakland.</li>
                </ul>
            </div>

            <p style="font-size: 16px; line-height: 1.6; color: #6F6757; font-style: italic;">
                See you soon,<br>
                The Stillpoint Team
            </p>
        </div>
        """

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        
        try:
            msg.send()
        except Exception as e:
            # If the email fails, print to console so the API request doesn't crash
            print(f"Failed to send email: {e}")


            
class StudioInfoView(generics.RetrieveAPIView):
    """GET /api/studio/"""
    serializer_class = StudioInfoSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        obj, _ = StudioInfo.objects.get_or_create(pk=1)
        return obj


# ---------- Admin-facing endpoints (auth required) ----------

class AdminBookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("yoga_class", "yoga_class__practice").all()
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "yoga_class", "session_date", "is_first_class"]
    search_fields = ["student_name", "student_email"]
    ordering_fields = ["session_date", "created_at"]


class AdminFreeClassRequestViewSet(viewsets.ModelViewSet):
    queryset = FreeClassRequest.objects.all()
    serializer_class = FreeClassRequestSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "preferred_practice", "preferred_time"]
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["created_at", "status"]


class AdminYogaClassViewSet(viewsets.ModelViewSet):
    """Full CRUD for classes — admin only."""
    queryset = YogaClass.objects.select_related("practice", "teacher", "room").all()
    serializer_class = YogaClassSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["day_of_week", "practice", "teacher", "room", "is_active"]
    ordering_fields = ["day_of_week", "start_time"]