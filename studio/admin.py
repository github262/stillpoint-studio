# from django.contrib import admin

# # Register your models here.


from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Practice, StudioRoom, Teacher, YogaClass, Booking,
    FreeClassRequest, StudioInfo,
)


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ("name", "tag", "tagline", "intensity", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("tag", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tagline", "description")


@admin.register(StudioRoom)
class StudioRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "has_natural_light", "is_skylit")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")  # <-- Add this line

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "years_teaching", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "years_teaching")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "role", "discipline")
    filter_horizontal = ("practices",)


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ("session_date", "student_name", "student_email", "status", "is_first_class")
    readonly_fields = ("created_at",)
    can_delete = True


@admin.register(YogaClass)
class YogaClassAdmin(admin.ModelAdmin):
    list_display = ("__str__", "practice", "teacher", "room",
                    "day_of_week", "start_time", "duration_minutes",
                    "effective_capacity", "is_active")
    list_editable = ("is_active",)
    list_filter = ("day_of_week", "practice", "teacher", "room", "is_active")
    search_fields = ("subtitle", "description_override")
    autocomplete_fields = ("practice", "teacher", "room")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("student_name", "yoga_class", "session_date",
                    "status", "is_first_class", "created_at")
    list_filter = ("status", "is_first_class", "session_date",
                   "yoga_class__practice", "yoga_class__teacher")
    search_fields = ("student_name", "student_email", "student_phone", "notes")
    date_hierarchy = "session_date"
    autocomplete_fields = ("yoga_class",)
    actions = ["mark_confirmed", "mark_waitlist", "mark_cancelled", "mark_noshow"]

    @admin.action(description="Mark selected as confirmed")
    def mark_confirmed(self, request, queryset):
        queryset.update(status="confirmed")

    @admin.action(description="Mark selected as waitlist")
    def mark_waitlist(self, request, queryset):
        queryset.update(status="waitlist")

    @admin.action(description="Mark selected as cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")

    @admin.action(description="Mark selected as no-show")
    def mark_noshow(self, request, queryset):
        queryset.update(status="noshow")


@admin.register(FreeClassRequest)
class FreeClassRequestAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "preferred_practice",
                    "preferred_time", "status", "created_at")
    list_filter = ("status", "preferred_practice", "preferred_time")
    list_editable = ("status",)
    search_fields = ("first_name", "last_name", "email", "phone", "notes")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_contacted", "mark_booked", "mark_closed"]

    @admin.action(description="Mark as contacted")
    def mark_contacted(self, request, queryset):
        queryset.update(status="contacted")

    @admin.action(description="Mark as booked")
    def mark_booked(self, request, queryset):
        queryset.update(status="booked")

    @admin.action(description="Mark as closed")
    def mark_closed(self, request, queryset):
        queryset.update(status="closed")

@admin.register(StudioInfo)
class StudioInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "state", "phone", "email")
    fieldsets = (
        ("Studio", {"fields": ("name", "tagline", "founded_year", "hours")}),
        ("Address", {"fields": ("address_line_1", "address_line_2",
                                "city", "state", "postal_code")}),
        ("Contact", {"fields": ("phone", "email")}),
    )


