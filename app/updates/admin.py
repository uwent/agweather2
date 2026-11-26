from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe

from updates.models import ApiUseReport, ChangelogEntry
from updates.render import markdown_html


@admin.register(ChangelogEntry)
class ChangelogEntryAdmin(admin.ModelAdmin):
    """Entries for `/changelog`, its feed and `GET /api/v2/changelog` (D112). Write them for the public."""

    list_display = ["date", "kind", "title", "published", "banner_until", "banner_now"]
    list_filter = ["kind", "published"]
    search_fields = ["title", "body"]
    date_hierarchy = "date"
    readonly_fields = ["preview", "created_at", "updated_at"]
    fields = ["kind", "date", "title", "body", "preview", "published", "banner_until", "model_id", "endpoint"]
    actions = ["publish", "unpublish"]

    @admin.display(boolean=True, description="Banner up now")
    def banner_now(self, entry: ChangelogEntry) -> bool:
        return entry.published and entry.banner_until is not None and entry.banner_until > timezone.now()

    @admin.display(description="Preview")
    def preview(self, entry: ChangelogEntry) -> str:
        # Safe: raw HTML in the body is escaped (updates.render)
        return mark_safe(markdown_html(entry.body)) if entry.body else "(Save to see the body as it will be shown.)"

    @admin.action(description="Publish the selected entries")
    def publish(self, request, queryset) -> None:
        for entry in queryset:  # save(), not update(), so updated_at (and the API's ETag) moves
            entry.published = True
            entry.save()

    @admin.action(description="Unpublish the selected entries")
    def unpublish(self, request, queryset) -> None:
        for entry in queryset:
            entry.published = False
            entry.save()


SUBMITTED = [
    "name",
    "organization",
    "email",
    "uses",
    "areas",
    "endpoints",
    "frequency",
    "notify",
    "client",
    "submitted_at",
]


@admin.register(ApiUseReport)
class ApiUseReportAdmin(admin.ModelAdmin):
    """What people sent through `/api-use` (D112): read, mark reviewed, keep notes."""

    list_display = ["submitted_at", "name", "organization", "email", "frequency", "notify", "reviewed"]
    list_filter = ["reviewed", "frequency", "notify"]
    search_fields = ["name", "organization", "email", "uses"]
    date_hierarchy = "submitted_at"
    readonly_fields = SUBMITTED
    fields = [*SUBMITTED, "reviewed", "notes"]
    actions = ["mark_reviewed"]

    def has_add_permission(self, request) -> bool:
        return False

    @admin.action(description="Mark the selected reports reviewed")
    def mark_reviewed(self, request, queryset) -> None:
        queryset.update(reviewed=True)
