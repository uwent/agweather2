from django.db import models


class IngestRecord(models.Model):
    """One ingest run of a block of hours: a backfill block or an hourly-job run. Which source filled each hour
    is in the hourly store's metadata; this is the run history behind the admin list and the health check."""

    class Kind(models.TextChoices):
        BACKFILL = "backfill"
        HOURLY = "hourly"
        FORECAST = "forecast"  # a published NBM run: first_hour and hours are its valid hours

    class Status(models.TextChoices):
        OK = "ok"
        PARTIAL = "partial", "Partial (hours failed or missing)"
        FAILED = "failed"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    box = models.CharField(max_length=64)
    first_hour = models.DateTimeField(help_text="UTC end of the first hour")
    hours = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()
    failed_hours = models.JSONField(default=list, blank=True, help_text="Hours whose fetch failed after retries")
    missing = models.JSONField(default=dict, blank=True, help_text="Hours without data, per variable")
    spikes = models.JSONField(default=dict, blank=True, help_text="Cells removed as spikes, per variable")
    out_of_range = models.JSONField(default=dict, blank=True, help_text="Cells outside the QC range, per variable")
    sources = models.JSONField(default=dict, blank=True, help_text="Hours per source, per variable")
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["kind", "-started_at"])]

    def __str__(self) -> str:
        return f"{self.kind} {self.first_hour:%Y-%m-%d %H}Z +{self.hours} h: {self.status}"


class WeatherCellCache(models.Model):
    """Open-Meteo hours for one O1280 cell over a span of UTC days from one endpoint (D42): the forecast's span
    (expires after 3 hours), or a month of history (a whole past month never expires; one reaching into the last
    week expires after a day)."""

    cell = models.CharField(max_length=32, help_text="o1280:ring:index")
    endpoint = models.CharField(max_length=16)
    first_day = models.DateField()
    last_day = models.DateField()
    fetched_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Empty: never")
    calls = models.FloatField(help_text="Calls Open-Meteo counted for it")
    data = models.BinaryField(help_text="Compressed arrays: each catalog variable's hours ending 00Z first_day on")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cell", "endpoint", "first_day"], name="one_span_per_start")]
        indexes = [models.Index(fields=["cell", "first_day"])]

    def __str__(self) -> str:
        return f"{self.cell} {self.endpoint} {self.first_day}–{self.last_day}"


class DatasetStatus(models.Model):
    """What `/api/v2/status` says about each dataset, read from the stores themselves (not logged beside the writes)
    whenever the write lock is released and when the worker starts (`ops.status.refresh_dataset_status`), so the
    API answers from a row instead of opening every store."""

    class Dataset(models.TextChoices):
        HOURLY = "hourly"
        DAILY = "daily"
        CUMULATIVE = "cumulative"
        FORECAST = "forecast"  # the published run

    dataset = models.CharField(max_length=16, choices=Dataset.choices, primary_key=True)
    first = models.DateTimeField(null=True, help_text="First hour (UTC end), or first day")
    last = models.DateTimeField(null=True, help_text="Last hour (UTC end), or last day rolled up")
    last_by_source = models.JSONField(default=dict, blank=True, help_text="Hourly: each source's newest hour")
    stale = models.JSONField(default=dict, blank=True, help_text="Year → derived variables from older code (D29)")
    details = models.JSONField(default=dict, blank=True, help_text="Forecast: cycle, last hour, last observed hour")
    refreshed_at = models.DateTimeField()

    class Meta:
        verbose_name_plural = "dataset statuses"

    def __str__(self) -> str:
        return f"{self.dataset}: {self.first} to {self.last}"
