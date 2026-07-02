from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PracticeViewSet, TeacherViewSet, StudioRoomViewSet,
    ScheduleView, BookingCreateView, BookingDetailView,
    FreeClassRequestView, StudioInfoView,
    AdminBookingViewSet, AdminFreeClassRequestViewSet, AdminYogaClassViewSet,
)

router = DefaultRouter()
router.register(r"practices", PracticeViewSet, basename="practice")
router.register(r"teachers", TeacherViewSet, basename="teacher")
router.register(r"rooms", StudioRoomViewSet, basename="room")
router.register(r"admin/bookings", AdminBookingViewSet, basename="admin-booking")
router.register(r"admin/requests", AdminFreeClassRequestViewSet, basename="admin-request")
router.register(r"admin/classes", AdminYogaClassViewSet, basename="admin-class")

urlpatterns = [
    path("", include(router.urls)),
    path("schedule/", ScheduleView.as_view(), name="schedule"),
    path("bookings/", BookingCreateView.as_view(), name="booking-create"),
    path("bookings/<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path("free-class/", FreeClassRequestView.as_view(), name="free-class"),
    path("studio/", StudioInfoView.as_view(), name="studio-info"),
]