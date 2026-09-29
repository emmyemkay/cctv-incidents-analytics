from django.db import models


class DatasetUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class IncidentType(models.TextChoices):
        AUTO = "AUTO", "Auto-detect from filename"
        FIRE = "FIRE", "Fire"
        CRIME = "CRIME", "General crime"
        TRAFFIC = "TRAFFIC", "Traffic"
        CCTV = "CCTV", "CCTV detection"

    class ImportMethod(models.TextChoices):
        UPLOAD = "UPLOAD", "Web upload"
        BUNDLED = "BUNDLED", "Bundled dataset"
        COMMAND = "COMMAND", "Management command"

    file = models.FileField(upload_to="datasets/%Y/%m/", blank=True)
    original_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, blank=True, db_index=True)
    import_method = models.CharField(
        max_length=20,
        choices=ImportMethod.choices,
        default=ImportMethod.UPLOAD,
        db_index=True,
    )
    incident_type = models.CharField(max_length=20, choices=IncidentType.choices, default=IncidentType.AUTO)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    rows_seen = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)
    rows_skipped = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=80, blank=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["file_hash", "status"], name="idx_upload_hash_status"),
        ]

    def __str__(self):
        return self.original_name


class Incident(models.Model):
    class SourceType(models.TextChoices):
        FIRE = "FIRE", "Fire"
        CRIME = "CRIME", "General crime"
        TRAFFIC = "TRAFFIC", "Traffic"
        CCTV = "CCTV", "CCTV detection"

    class Origin(models.TextChoices):
        UPLOAD = "UPLOAD", "File upload"
        STREAM = "STREAM", "Real-time stream"
        COMMAND = "COMMAND", "Management command"

    event_id = models.CharField(max_length=80)
    producer_id = models.CharField(max_length=120, blank=True, db_index=True)
    payload_version = models.CharField(max_length=30, blank=True, default="1.0")
    source_type = models.CharField(max_length=20, choices=SourceType.choices, db_index=True)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.UPLOAD, db_index=True)
    reported_at = models.DateTimeField(db_index=True)
    incident_location = models.TextField(blank=True)
    case_nature = models.CharField(max_length=255, blank=True, db_index=True)
    category = models.CharField(max_length=255, blank=True, db_index=True)
    sub_category = models.CharField(max_length=255, blank=True)
    reporting_type = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    governing_branch = models.CharField(max_length=255, blank=True, db_index=True)
    police_station = models.CharField(max_length=255, blank=True, db_index=True)
    create_room = models.CharField(max_length=255, blank=True)
    feedback_content = models.TextField(blank=True)
    processing_result = models.TextField(blank=True)
    event_status = models.CharField(max_length=100, blank=True, db_index=True)
    longitude = models.FloatField(null=True, blank=True, db_index=True)
    latitude = models.FloatField(null=True, blank=True, db_index=True)

    # Optional fields for events created by a CCTV/video analytics engine.
    camera_id = models.CharField(max_length=120, blank=True, db_index=True)
    detection_label = models.CharField(max_length=120, blank=True, db_index=True)
    confidence = models.FloatField(null=True, blank=True)
    snapshot_url = models.URLField(blank=True)

    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "producer_id", "event_id"],
                name="uq_incident_producer_event",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__isnull=True) | models.Q(longitude__gte=-180, longitude__lte=180),
                name="ck_incident_longitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(latitude__isnull=True) | models.Q(latitude__gte=-90, latitude__lte=90),
                name="ck_incident_latitude_range",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__isnull=True) | models.Q(confidence__gte=0, confidence__lte=1),
                name="ck_incident_confidence_range",
            ),
        ]
        indexes = [
            models.Index(fields=["source_type", "reported_at"], name="idx_source_reported"),
            models.Index(fields=["police_station", "reported_at"], name="idx_station_reported"),
            models.Index(fields=["event_status", "reported_at"], name="idx_status_reported"),
            models.Index(fields=["category", "reported_at"], name="idx_category_reported"),
            models.Index(fields=["governing_branch", "reported_at"], name="idx_branch_reported"),
            models.Index(fields=["origin", "created_at"], name="idx_origin_created"),
            models.Index(fields=["source_type", "category"], name="idx_source_category"),
            models.Index(fields=["producer_id", "reported_at"], name="idx_producer_reported"),
            models.Index(fields=["police_station", "event_status"], name="idx_station_status"),
        ]

    def save(self, *args, **kwargs):
        from incidents.services.normalization import normalize_operational_area

        self.police_station = normalize_operational_area(self.police_station)
        self.governing_branch = normalize_operational_area(self.governing_branch)
        super().save(*args, **kwargs)

    @property
    def analytical_category(self):
        """Category used everywhere: Category, then Sub-Category, then Uncategorised."""
        from incidents.services.categories import resolve_category

        return resolve_category(self.category, self.sub_category)

    @property
    def analytical_category_key(self):
        from incidents.services.categories import category_colour_key

        return category_colour_key(self.analytical_category)

    @property
    def analytical_category_colour(self):
        from incidents.services.categories import category_colour

        return category_colour(self.analytical_category)

    @property
    def has_coordinates(self):
        return self.longitude is not None and self.latitude is not None

    def __str__(self):
        return f"{self.source_type}: {self.event_id}"


class AnalyticsSnapshot(models.Model):
    """Durable fallback for expensive pre-computed analytics payloads."""

    key = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(default=dict)
    source_row_count = models.PositiveBigIntegerField(default=0)
    latest_reported_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return self.key
