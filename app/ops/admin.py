from django.contrib import admin, messages
from django.utils import timezone

from ops import openmeteo_usage
from ops.models import ApiUsage, IngestRecord, OpenMeteoUsage


@admin.register(IngestRecord)
class IngestRecordAdmin(admin.ModelAdmin):
    list_display = ["started_at", "kind", "status", "first_hour", "hours", "box", "failed_count", "duration"]
    list_filter = ["kind", "status", "box"]
    date_hierarchy = "first_hour"
    readonly_fields = [f.name for f in IngestRecord._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    @admin.display(description="Failed hours")
    def failed_count(self, record: IngestRecord) -> int:
        return len(record.failed_hours)

    @admin.display(description="Duration")
    def duration(self, record: IngestRecord) -> str:
        return f"{(record.finished_at - record.started_at).total_seconds():.0f} s"


@admin.register(ApiUsage)
class ApiUsageAdmin(admin.ModelAdmin):
    """The API's use by client and minute (D69): who uses it, how much, and who reaches the limit."""

    list_display = ["minute", "client", "requests", "cost"]
    search_fields = ["client"]
    date_hierarchy = "minute"
    ordering = ["-minute", "-cost"]
    readonly_fields = [f.name for f in ApiUsage._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


@admin.register(OpenMeteoUsage)
class OpenMeteoUsageAdmin(admin.ModelAdmin):
    """Open-Meteo's use by UTC day and endpoint (D115), with the billing month's total against the plan above the
    list, and a warning past `OPEN_METEO_WARN_SHARE` of it."""

    list_display = ["day", "endpoint", "requests", "calls", "failed"]
    list_filter = ["endpoint"]
    date_hierarchy = "day"
    readonly_fields = [f.name for f in OpenMeteoUsage._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def changelist_view(self, request, extra_context=None):
        usage = openmeteo_usage.period_usage(timezone.now())
        messages.info(request, openmeteo_usage.summary(usage))
        for warning in openmeteo_usage.warnings_for(usage):
            messages.warning(request, warning)
        return super().changelist_view(request, extra_context=extra_context)
