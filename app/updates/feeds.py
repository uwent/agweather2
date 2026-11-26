"""The changelog as an Atom feed (`/changelog.atom`, D112): API users have no accounts, so a feed is how they follow
changes."""

from datetime import datetime, time

from django.contrib.syndication.views import Feed
from django.utils import timezone
from django.utils.feedgenerator import Atom1Feed

from updates.models import ChangelogEntry
from updates.render import markdown_html

ENTRIES = 50


class ChangelogFeed(Feed):
    feed_type = Atom1Feed
    title = "AgWeather changes and announcements"
    link = "/changelog"
    subtitle = (
        "Changes to AgWeather's data, models and API, and notices of outages, from the University of Wisconsin–Madison."
    )
    author_name = "AgWeather, University of Wisconsin–Madison"

    def items(self):
        return ChangelogEntry.objects.visible()[:ENTRIES]

    def item_title(self, item: ChangelogEntry) -> str:
        return item.title

    def item_description(self, item: ChangelogEntry) -> str:
        return markdown_html(item.body)

    def item_link(self, item: ChangelogEntry) -> str:
        return f"/changelog#entry-{item.pk}"

    def item_pubdate(self, item: ChangelogEntry) -> datetime:
        return timezone.make_aware(datetime.combine(item.date, time(12)))

    def item_updateddate(self, item: ChangelogEntry) -> datetime:
        return item.updated_at

    def item_categories(self, item: ChangelogEntry) -> list[str]:
        return [item.get_kind_display()]  # pyright: ignore[reportAttributeAccessIssue]
