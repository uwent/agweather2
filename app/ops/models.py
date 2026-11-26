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


class ApiUsage(models.Model):
    """The API's use by one client in one minute (D69): the requests it made and what they cost, which
    `api.ratelimit` charges by the server time each took. Rows older than a week are deleted (`housekeeping`)."""

    client = models.CharField(max_length=64, help_text="IPv4 address, or IPv6 /64 network")
    minute = models.DateTimeField(help_text="The minute's start (UTC)")
    requests = models.IntegerField(default=0)
    cost = models.IntegerField(default=0, help_text="Units: 1 a request, plus 1 per API_RATE_UNIT_MS of server time")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "minute"], name="one_row_per_client_minute")]
        indexes = [models.Index(fields=["minute"])]

    def __str__(self) -> str:
        return f"{self.client} {self.minute:%Y-%m-%d %H:%M}Z: {self.requests} requests, cost {self.cost}"


class OpenMeteoUsage(models.Model):
    """Requests made to Open-Meteo in one UTC day from one endpoint, and the calls they count against the plan (D115):
    every attempt, failures and retries included (`ops.openmeteo_usage`). Kept two years (`housekeeping`)."""

    day = models.DateField(help_text="UTC day")
    endpoint = models.CharField(max_length=16, help_text="forecast, historical or archive")
    requests = models.IntegerField(default=0, help_text="HTTP requests, failed ones included")
    calls = models.FloatField(default=0, help_text="Calls Open-Meteo counts for them (more for many variables or days)")
    failed = models.IntegerField(default=0, help_text="Requests that failed (no answer, an error status, or no data)")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["day", "endpoint"], name="one_row_per_day_endpoint")]
        ordering = ["-day", "endpoint"]
        verbose_name = "Open-Meteo usage"
        verbose_name_plural = "Open-Meteo usage"

    def __str__(self) -> str:
        return f"{self.day} {self.endpoint}: {self.requests} requests, {self.calls:g} calls"


class ForecastScore(models.Model):
    """One kept forecast run's score for one variable on one lead day against the archive's (D113,
    `agdata.verification`): over the covered cells where both are known, the error forecast − observed in the
    catalog's unit. Pool rows weighted by `n` (RMSE as √(Σ n·rmse² / Σ n), exactly). Kept indefinitely (~250,000 rows a
    year); a day is scored again when the archive rewrites it (`observed_written`)."""

    cycle = models.DateTimeField(help_text="The NBM run's cycle (UTC)")
    lead = models.PositiveSmallIntegerField(help_text="Days after the cycle's grid day (1-10)")
    valid_day = models.DateField(help_text="The grid day forecast")
    variable = models.CharField(max_length=64, help_text="Daily variable or model ingredient, or dd_sine_50_86")
    n = models.IntegerField(help_text="Cells with both a forecast and an observed value")
    bias = models.FloatField(null=True, help_text="Mean error (forecast − observed); empty when n is 0")
    mae = models.FloatField(null=True, help_text="Mean absolute error")
    rmse = models.FloatField(null=True, help_text="Root mean square error")
    hits = models.IntegerField(null=True, help_text="Precipitation: cells wet in both (0.01 in or more)")
    misses = models.IntegerField(null=True, help_text="Precipitation: wet observed, dry forecast")
    false_alarms = models.IntegerField(null=True, help_text="Precipitation: wet forecast, dry observed")
    observed_written = models.DateTimeField(help_text="When the archive last wrote the day's values scored")
    scored_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cycle", "lead", "variable"], name="one_score_per_run_lead_variable")
        ]
        indexes = [models.Index(fields=["variable", "lead", "valid_day"])]

    def __str__(self) -> str:
        return f"{self.cycle:%Y-%m-%d %H}Z lead {self.lead} {self.variable}: n {self.n}, MAE {self.mae}"
