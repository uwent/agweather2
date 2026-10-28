from django.contrib import admin

from ops.models import IngestRecord


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
