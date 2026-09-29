from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Case, CharField, Count, F, Max, Min, Q, Value, When
from django.db.models.functions import (
    ExtractHour,
    ExtractIsoWeekDay,
    ExtractMonth,
    ExtractYear,
    Lower,
    Trim,
    TruncDate,
    TruncMonth,
)
from django.utils import timezone
from django.utils.dateparse import parse_date

from incidents.models import Incident
from incidents.services.categories import (
    UNCATEGORISED_LABEL,
    category_colour,
    category_colour_key,
    resolve_category,
)
from incidents.services.normalization import COMMAND_CENTER_LABEL

NON_GEOGRAPHIC_AREAS = {"UNKNOWN", "N/A", "NA"}
UGANDA_BOUNDS = {"min_lat": -1.6, "max_lat": 4.5, "min_lon": 29.4, "max_lon": 35.1}
CLOSED_STATUSES = {"CLOSED", "FED BACK", "DELIVERED"}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ANALYTICAL_CATEGORY_FIELD = "analytical_category"

# Ordered to mirror the strongest analytical sequence in the supplied GIS report.
# Categories not present in a filtered dataset are skipped, and the list is then
# completed with the highest-volume mapped categories.
MAP_REPORT_PRIORITY_CATEGORIES = [
    "Death (by shooting)",
    "Traffic and Road Safety Act (Not categorised)",
    "Death (Traffic Accidents)",
    "Breakings",
    "Death (Aggravated Domestic Violence)",
    "Child Related Offences",
    "Robberies",
    "Sex Related Offences",
    "Thefts",
    "Assaults",
]


def with_analytical_category(queryset):
    """Annotate Category with Sub-Category used only when Category is blank."""
    return queryset.annotate(
        _category_trim=Trim("category"),
        _sub_category_trim=Trim("sub_category"),
    ).annotate(
        analytical_category=Case(
            When(_category_trim__gt="", then=F("_category_trim")),
            When(_sub_category_trim__gt="", then=F("_sub_category_trim")),
            default=Value(UNCATEGORISED_LABEL),
            output_field=CharField(max_length=255),
        )
    )


def analytical_category_values(queryset=None):
    """Return the complete ordered analytical category list for filters."""
    qs = with_analytical_category(queryset if queryset is not None else Incident.objects.all())
    return list(qs.values_list(ANALYTICAL_CATEGORY_FIELD, flat=True).distinct().order_by(ANALYTICAL_CATEGORY_FIELD))


def distinct_analytical_categories(queryset, include_uncategorised=True):
    qs = with_analytical_category(queryset)
    if not include_uncategorised:
        qs = qs.exclude(analytical_category=UNCATEGORISED_LABEL)
    return qs.values(ANALYTICAL_CATEGORY_FIELD).distinct().count()


def classified_incident_count(queryset):
    """Count records where Category exists or Sub-Category can fill it."""
    return with_analytical_category(queryset).exclude(analytical_category=UNCATEGORISED_LABEL).count()


def filtered_incidents(params):
    qs = Incident.objects.all()
    source = params.get("source")
    year = params.get("year")
    status = params.get("status")
    station = params.get("station")
    branch = params.get("branch")
    category = params.get("category")
    sub_category = params.get("sub_category")
    command_center = params.get("command_center")
    coordinate = params.get("coordinate")
    origin = params.get("origin")
    date_from = parse_date(params.get("date_from", ""))
    date_to = parse_date(params.get("date_to", ""))
    query = params.get("q")

    if source:
        qs = qs.filter(source_type=source)
    if year and str(year).isdigit():
        qs = qs.filter(reported_at__year=int(year))
    if status:
        qs = qs.filter(event_status=status)
    if station:
        qs = qs.filter(police_station=station)
    if branch:
        qs = qs.filter(governing_branch=branch)
    if category:
        qs = with_analytical_category(qs).filter(analytical_category=category)
    if sub_category:
        qs = qs.filter(sub_category=sub_category)
    if command_center == "only":
        qs = qs.filter(Q(police_station=COMMAND_CENTER_LABEL) | Q(governing_branch=COMMAND_CENTER_LABEL))
    elif command_center == "exclude":
        qs = qs.exclude(Q(police_station=COMMAND_CENTER_LABEL) | Q(governing_branch=COMMAND_CENTER_LABEL))
    if origin:
        qs = qs.filter(origin=origin)
    if coordinate == "mapped":
        qs = qs.filter(longitude__isnull=False, latitude__isnull=False)
    elif coordinate == "unmapped":
        qs = qs.filter(Q(longitude__isnull=True) | Q(latitude__isnull=True))
    if date_from:
        qs = qs.filter(reported_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(reported_at__date__lte=date_to)
    if query:
        qs = qs.filter(
            Q(event_id__icontains=query)
            | Q(incident_location__icontains=query)
            | Q(description__icontains=query)
            | Q(police_station__icontains=query)
            | Q(governing_branch__icontains=query)
            | Q(category__icontains=query)
            | Q(sub_category__icontains=query)
            | Q(camera_id__icontains=query)
        )
    return qs


def count_series(queryset, field: str, limit: int = 12):
    if field == "category":
        rows = list(
            with_analytical_category(queryset)
            .values(ANALYTICAL_CATEGORY_FIELD)
            .annotate(total=Count("id"))
            .order_by("-total", ANALYTICAL_CATEGORY_FIELD)[:limit]
        )
        return [
            {"category": row[ANALYTICAL_CATEGORY_FIELD], "total": row["total"]}
            for row in rows
        ]
    return list(
        queryset.exclude(**{field: ""})
        .values(field)
        .annotate(total=Count("id"))
        .order_by("-total", field)[:limit]
    )


def hotspot_queryset(queryset, include_command_center: bool = True):
    qs = queryset.exclude(police_station="")
    for value in NON_GEOGRAPHIC_AREAS:
        qs = qs.exclude(police_station__iexact=value)
    if not include_command_center:
        qs = qs.exclude(police_station=COMMAND_CENTER_LABEL)
    return qs


def _monthly_series(queryset):
    rows = list(
        queryset.annotate(month=TruncMonth("reported_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    return [
        {"month": row["month"].strftime("%Y-%m-01") if row["month"] else "", "total": row["total"]}
        for row in rows
    ]


def _year_series(queryset):
    return list(
        queryset.annotate(year=ExtractYear("reported_at"))
        .values("year")
        .annotate(total=Count("id"))
        .order_by("year")
    )


def _hotspot_trend(queryset, hotspot_names: list[str]):
    if not hotspot_names:
        return {"months": [], "areas": [], "datasets": []}
    rows = list(
        queryset.filter(police_station__in=hotspot_names)
        .annotate(month=TruncMonth("reported_at"))
        .values("month", "police_station")
        .annotate(total=Count("id"))
        .order_by("month", "police_station")
    )
    month_keys = sorted({row["month"] for row in rows if row["month"]})
    lookup = {(row["month"], row["police_station"]): row["total"] for row in rows if row["month"]}
    return {
        "months": [month.strftime("%Y-%m-01") for month in month_keys],
        "areas": hotspot_names,
        "datasets": [
            {"area": area, "values": [lookup.get((month, area), 0) for month in month_keys]}
            for area in hotspot_names
        ],
    }


def _category_area_join(queryset, area_limit: int = 8, category_limit: int = 6, include_command_center: bool = True):
    geographic = hotspot_queryset(queryset, include_command_center=include_command_center)
    top_areas = [row["police_station"] for row in count_series(geographic, "police_station", area_limit)]
    top_categories = [row["category"] for row in count_series(geographic, "category", category_limit)]
    if not top_areas or not top_categories:
        return {"areas": top_areas, "categories": top_categories, "datasets": [], "matrix": []}

    rows = list(
        with_analytical_category(geographic)
        .filter(police_station__in=top_areas, analytical_category__in=top_categories)
        .values("police_station", ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"))
        .order_by("police_station", ANALYTICAL_CATEGORY_FIELD)
    )
    counts = defaultdict(int)
    for row in rows:
        counts[(row["police_station"], row[ANALYTICAL_CATEGORY_FIELD])] = row["total"]

    matrix = []
    for area in top_areas:
        values = [counts[(area, category)] for category in top_categories]
        dominant_index = max(range(len(values)), key=values.__getitem__) if values else 0
        matrix.append(
            {
                "area": area,
                "total": sum(values),
                "counts": values,
                "dominant_category": top_categories[dominant_index] if values else "",
                "dominant_total": values[dominant_index] if values else 0,
            }
        )
    return {
        "areas": top_areas,
        "categories": top_categories,
        "datasets": [
            {"category": category, "values": [counts[(area, category)] for area in top_areas]}
            for category in top_categories
        ],
        "matrix": matrix,
    }


def _category_time_analysis(queryset, category_limit: int = 6):
    category_names = [row["category"] for row in count_series(queryset, "category", category_limit)]
    empty = {
        "months": [], "years": [], "month_names": list(calendar.month_abbr)[1:], "categories": [],
        "monthly_datasets": [], "yearly_datasets": [], "seasonal_datasets": [], "year_matrix": [],
    }
    if not category_names:
        return empty

    categorized = with_analytical_category(queryset).filter(analytical_category__in=category_names)
    monthly_rows = list(
        categorized.annotate(month=TruncMonth("reported_at"))
        .values("month", ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"))
        .order_by("month", ANALYTICAL_CATEGORY_FIELD)
    )
    month_keys = sorted({row["month"] for row in monthly_rows if row["month"]})
    monthly_lookup = {
        (row["month"], row[ANALYTICAL_CATEGORY_FIELD]): row["total"]
        for row in monthly_rows if row["month"]
    }

    yearly_rows = list(
        categorized.annotate(year=ExtractYear("reported_at"))
        .values("year", ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"))
        .order_by("year", ANALYTICAL_CATEGORY_FIELD)
    )
    years = sorted({row["year"] for row in yearly_rows if row["year"] is not None})
    yearly_lookup = {
        (row["year"], row[ANALYTICAL_CATEGORY_FIELD]): row["total"]
        for row in yearly_rows if row["year"] is not None
    }

    seasonal_rows = list(
        categorized.annotate(month_number=ExtractMonth("reported_at"))
        .values("month_number", ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"))
        .order_by("month_number", ANALYTICAL_CATEGORY_FIELD)
    )
    seasonal_lookup = {
        (row["month_number"], row[ANALYTICAL_CATEGORY_FIELD]): row["total"]
        for row in seasonal_rows if row["month_number"]
    }

    return {
        "months": [month.strftime("%Y-%m-01") for month in month_keys],
        "years": years,
        "month_names": list(calendar.month_abbr)[1:],
        "categories": category_names,
        "monthly_datasets": [
            {"category": category, "values": [monthly_lookup.get((month, category), 0) for month in month_keys]}
            for category in category_names
        ],
        "yearly_datasets": [
            {"category": category, "values": [yearly_lookup.get((year, category), 0) for year in years]}
            for category in category_names
        ],
        "seasonal_datasets": [
            {"category": category, "values": [seasonal_lookup.get((month, category), 0) for month in range(1, 13)]}
            for category in category_names
        ],
        "year_matrix": [
            {
                "category": category,
                "counts": [yearly_lookup.get((year, category), 0) for year in years],
                "total": sum(yearly_lookup.get((year, category), 0) for year in years),
            }
            for category in category_names
        ],
    }


def _time_patterns(queryset, category_limit: int = 5):
    hour_rows = list(
        queryset.annotate(hour=ExtractHour("reported_at"))
        .values("hour").annotate(total=Count("id")).order_by("hour")
    )
    by_hour_lookup = {row["hour"]: row["total"] for row in hour_rows if row["hour"] is not None}
    by_hour = [{"hour": hour, "label": f"{hour:02d}:00", "total": by_hour_lookup.get(hour, 0)} for hour in range(24)]

    weekday_rows = list(
        queryset.annotate(weekday=ExtractIsoWeekDay("reported_at"))
        .values("weekday").annotate(total=Count("id")).order_by("weekday")
    )
    weekday_lookup = {row["weekday"]: row["total"] for row in weekday_rows if row["weekday"]}
    by_weekday = [{"weekday": day, "day_number": idx, "total": weekday_lookup.get(idx, 0)} for idx, day in enumerate(WEEKDAYS, 1)]

    heat_rows = list(
        queryset.annotate(weekday=ExtractIsoWeekDay("reported_at"), hour=ExtractHour("reported_at"))
        .values("weekday", "hour").annotate(total=Count("id"))
    )
    heat_lookup = {(row["weekday"], row["hour"]): row["total"] for row in heat_rows}
    heatmap = [
        {"weekday": day, "day_number": day_number, "values": [heat_lookup.get((day_number, hour), 0) for hour in range(24)]}
        for day_number, day in enumerate(WEEKDAYS, 1)
    ]

    categories = [row["category"] for row in count_series(queryset, "category", category_limit)]
    category_rows = list(
        with_analytical_category(queryset)
        .filter(analytical_category__in=categories)
        .annotate(hour=ExtractHour("reported_at"))
        .values("hour", ANALYTICAL_CATEGORY_FIELD).annotate(total=Count("id"))
    )
    category_lookup = {
        (row["hour"], row[ANALYTICAL_CATEGORY_FIELD]): row["total"]
        for row in category_rows
    }
    category_hour = [
        {"category": category, "values": [category_lookup.get((hour, category), 0) for hour in range(24)]}
        for category in categories
    ]

    peak_hour = max(by_hour, key=lambda item: item["total"]) if by_hour else {"label": "—", "total": 0}
    peak_day = max(by_weekday, key=lambda item: item["total"]) if by_weekday else {"weekday": "—", "total": 0}
    daytime = sum(item["total"] for item in by_hour if 6 <= item["hour"] < 18)
    nighttime = sum(item["total"] for item in by_hour if item["hour"] < 6 or item["hour"] >= 18)
    weekday_total = sum(item["total"] for item in by_weekday[:5])
    weekend_total = sum(item["total"] for item in by_weekday[5:])

    return {
        "by_hour": by_hour,
        "by_weekday": by_weekday,
        "heatmap": heatmap,
        "hours": [f"{hour:02d}" for hour in range(24)],
        "category_hour": category_hour,
        "kpis": {
            "peak_hour": peak_hour["label"], "peak_hour_total": peak_hour["total"],
            "peak_day": peak_day["weekday"], "peak_day_total": peak_day["total"],
            "daytime": daytime, "nighttime": nighttime,
            "weekday": weekday_total, "weekend": weekend_total,
        },
    }


def _coordinate_quality(queryset):
    """Return mutually intelligible coordinate-quality groups for analytics and GIS reports."""
    total = queryset.count()
    present_qs = queryset.filter(longitude__isnull=False, latitude__isnull=False)
    missing_both = queryset.filter(longitude__isnull=True, latitude__isnull=True).count()
    partial = queryset.filter(
        Q(longitude__isnull=True, latitude__isnull=False)
        | Q(longitude__isnull=False, latitude__isnull=True)
    ).count()
    zero_pair = present_qs.filter(longitude=0, latitude=0).count()
    outside_q = (
        Q(longitude__lt=UGANDA_BOUNDS["min_lon"])
        | Q(longitude__gt=UGANDA_BOUNDS["max_lon"])
        | Q(latitude__lt=UGANDA_BOUNDS["min_lat"])
        | Q(latitude__gt=UGANDA_BOUNDS["max_lat"])
    )
    outside_uganda = present_qs.exclude(longitude=0, latitude=0).filter(outside_q).count()
    valid = mappable_incidents(queryset).count()
    invalid = zero_pair + outside_uganda
    missing = missing_both + partial
    return {
        "total": total,
        "mapped": present_qs.count(),
        "present": present_qs.count(),
        "valid": valid,
        "invalid": invalid,
        "missing": missing,
        "missing_both": missing_both,
        "partial": partial,
        "zero_pair": zero_pair,
        "outside_uganda": outside_uganda,
        "valid_pct": round(valid / total * 100, 1) if total else 0,
        "missing_pct": round(missing / total * 100, 1) if total else 0,
        "invalid_pct": round(invalid / total * 100, 1) if total else 0,
    }


def operational_insights(queryset):
    total = queryset.count()
    if not total:
        return []
    insights = []
    command_center = queryset.filter(police_station=COMMAND_CENTER_LABEL).count()
    cc_share = round(command_center / total * 100, 1)
    insights.append({
        "level": "info", "icon": "fa-building-shield", "title": "Command Center workload",
        "text": f"Command Center accounts for {cc_share}% of incidents in the current selection ({command_center:,} records).",
    })

    field_hotspots = count_series(hotspot_queryset(queryset, include_command_center=False), "police_station", 1)
    if field_hotspots:
        item = field_hotspots[0]
        insights.append({
            "level": "warning", "icon": "fa-location-crosshairs", "title": "Leading field hotspot",
            "text": f"{item['police_station']} is the leading field station with {item['total']:,} incidents.",
        })

    patterns = _time_patterns(queryset, category_limit=0)
    insights.append({
        "level": "info", "icon": "fa-clock", "title": "Peak reporting time",
        "text": f"The busiest hour is {patterns['kpis']['peak_hour']} with {patterns['kpis']['peak_hour_total']:,} incidents.",
    })

    coords = _coordinate_quality(queryset)
    coverage = round(coords["valid"] / total * 100, 1)
    level = "success" if coverage >= 80 else "warning" if coverage >= 50 else "danger"
    insights.append({
        "level": level, "icon": "fa-map-location-dot", "title": "Map readiness",
        "text": f"{coverage}% of incidents have coordinates within the expected Uganda boundary.",
    })

    monthly = _monthly_series(queryset)
    if len(monthly) >= 4:
        latest = monthly[-1]
        previous = monthly[-4:-1]
        average = sum(item["total"] for item in previous) / len(previous)
        if average:
            change = round((latest["total"] - average) / average * 100, 1)
            if abs(change) >= 20:
                direction = "above" if change > 0 else "below"
                insights.append({
                    "level": "danger" if change > 0 else "success", "icon": "fa-triangle-exclamation",
                    "title": "Monthly anomaly",
                    "text": f"The latest month is {abs(change)}% {direction} the preceding three-month average.",
                })
    return insights[:6]


def home_payload(queryset):
    total = queryset.count()
    coordinate = _coordinate_quality(queryset)
    streamed = queryset.filter(origin=Incident.Origin.STREAM).count()
    by_category = count_series(queryset, "category", 5)
    by_area = count_series(hotspot_queryset(queryset, include_command_center=False), "police_station", 5)
    top_category = by_category[0] if by_category else {"category": "No category", "total": 0}
    top_area = by_area[0] if by_area else {"police_station": "No field station", "total": 0}
    dates = queryset.aggregate(first=Min("reported_at"), latest=Max("reported_at"))
    command_center = queryset.filter(police_station=COMMAND_CENTER_LABEL).count()
    category_complete = classified_incident_count(queryset)
    return {
        "kpis": {
            "total": total, "mapped": coordinate["valid"],
            "mapped_pct": round(coordinate["valid"] / total * 100, 1) if total else 0,
            "streamed": streamed, "command_center": command_center,
            "command_center_pct": round(command_center / total * 100, 1) if total else 0,
            "category_pct": round(category_complete / total * 100, 1) if total else 0,
            "top_category": top_category["category"], "top_category_total": top_category["total"],
            "top_area": top_area["police_station"], "top_area_total": top_area["total"],
            "first_date": dates["first"], "latest_date": dates["latest"],
        },
        "by_source": count_series(queryset, "source_type", 10),
        "by_year": _year_series(queryset),
        "top_categories": by_category,
        "top_areas": by_area,
        "insights": operational_insights(queryset),
    }


def area_category_payload(queryset):
    geographic = hotspot_queryset(queryset)
    total = geographic.count()
    by_area = count_series(geographic, "police_station", 15)
    category_area = _category_area_join(queryset, area_limit=12, category_limit=8)
    top_area = by_area[0] if by_area else {"police_station": "No area", "total": 0}
    return {
        "kpis": {
            "total": total,
            "distinct_areas": geographic.values("police_station").distinct().count(),
            "distinct_categories": distinct_analytical_categories(geographic),
            "top_area": top_area["police_station"], "top_area_total": top_area["total"],
            "top_area_pct": round(top_area["total"] / total * 100, 1) if total else 0,
        },
        "by_area": by_area, "category_area": category_area, "station_pareto": _station_pareto(queryset),
        "hotspot_exclusions": sorted(NON_GEOGRAPHIC_AREAS),
    }


def category_time_payload(queryset):
    total = classified_incident_count(queryset)
    by_category = count_series(queryset, "category", 15)
    top_category = by_category[0] if by_category else {"category": "No category", "total": 0}
    years = list(
        queryset.annotate(year=ExtractYear("reported_at")).exclude(year=None)
        .values_list("year", flat=True).distinct().order_by("year")
    )
    category_time = _category_time_analysis(queryset, category_limit=8)
    return {
        "kpis": {
            "total": total,
            "distinct_categories": distinct_analytical_categories(queryset),
            "periods": len(category_time["months"]),
            "top_category": top_category["category"], "top_category_total": top_category["total"],
            "year_from": years[0] if years else None, "year_to": years[-1] if years else None,
        },
        "by_category": by_category, "by_month": _monthly_series(queryset), "category_time": category_time,
    }


def time_patterns_payload(queryset):
    patterns = _time_patterns(queryset, category_limit=6)
    patterns["total"] = queryset.count()
    return patterns


def command_center_payload(queryset):
    center_station = queryset.filter(police_station=COMMAND_CENTER_LABEL)
    center_branch = queryset.filter(governing_branch=COMMAND_CENTER_LABEL)
    any_center = queryset.filter(Q(police_station=COMMAND_CENTER_LABEL) | Q(governing_branch=COMMAND_CENTER_LABEL)).distinct()
    dispatched = queryset.filter(governing_branch=COMMAND_CENTER_LABEL).exclude(police_station__in=["", COMMAND_CENTER_LABEL])
    field = queryset.exclude(police_station=COMMAND_CENTER_LABEL)
    total = queryset.count()
    return {
        "kpis": {
            "total": any_center.count(), "station_total": center_station.count(), "branch_total": center_branch.count(),
            "dispatched": dispatched.count(), "field_total": field.count(),
            "share": round(any_center.count() / total * 100, 1) if total else 0,
        },
        "by_category": count_series(any_center, "category", 12),
        "by_status": count_series(any_center, "event_status", 10),
        "by_month": _monthly_series(any_center),
        "destinations": count_series(dispatched, "police_station", 15),
        "dispatch_category": count_series(dispatched, "category", 12),
        "source_mix": count_series(any_center, "source_type", 10),
    }


def dispatch_payload(queryset):
    eligible = queryset.exclude(governing_branch="").exclude(police_station="")
    # Calculate retention from grouped branch-to-station flows so casing differences are handled consistently.
    flow_rows = list(
        eligible.values("governing_branch", "police_station")
        .annotate(total=Count("id")).order_by("-total")
    )
    retained = sum(row["total"] for row in flow_rows if row["governing_branch"].strip().lower() == row["police_station"].strip().lower())
    transferred = sum(row["total"] for row in flow_rows) - retained
    top_flows = [row for row in flow_rows if row["governing_branch"].strip().lower() != row["police_station"].strip().lower()][:20]
    top_branches = [row["governing_branch"] for row in count_series(eligible, "governing_branch", 8)]
    top_stations = [row["police_station"] for row in count_series(eligible, "police_station", 10)]
    matrix_rows = list(
        eligible.filter(governing_branch__in=top_branches, police_station__in=top_stations)
        .values("governing_branch", "police_station").annotate(total=Count("id"))
    )
    lookup = {(row["governing_branch"], row["police_station"]): row["total"] for row in matrix_rows}
    matrix = [
        {"branch": branch, "counts": [lookup.get((branch, station), 0) for station in top_stations]}
        for branch in top_branches
    ]
    total = eligible.count()
    transfer_qs = eligible.exclude(governing_branch=F("police_station"))
    return {
        "kpis": {
            "eligible": total, "retained": retained, "transferred": transferred,
            "retention_pct": round(retained / total * 100, 1) if total else 0,
            "transfer_pct": round(transferred / total * 100, 1) if total else 0,
        },
        "top_flows": top_flows,
        "transfer_categories": count_series(transfer_qs, "category", 12),
        "branches": top_branches, "stations": top_stations, "matrix": matrix,
        "branch_totals": count_series(eligible, "governing_branch", 12),
        "station_totals": count_series(eligible, "police_station", 12),
    }


def data_quality_payload(queryset):
    total = queryset.count()
    coordinate = _coordinate_quality(queryset)
    metrics = {
        "missing_category": queryset.filter(category="").count(),
        "missing_sub_category": queryset.filter(sub_category="").count(),
        "missing_both_category_fields": queryset.filter(category="", sub_category="").count(),
        "subcategory_used_as_category": queryset.filter(category="").exclude(sub_category="").count(),
        "missing_description": queryset.filter(description="").count(),
        "missing_station": queryset.filter(police_station="").count(),
        "missing_coordinates": queryset.filter(Q(longitude__isnull=True) | Q(latitude__isnull=True)).count(),
        "missing_feedback": queryset.filter(feedback_content="").count(),
        "missing_processing": queryset.filter(processing_result="").count(),
        "invalid_coordinates": coordinate["invalid"],
    }
    for key, value in list(metrics.items()):
        metrics[f"{key}_pct"] = round(value / total * 100, 1) if total else 0

    yearly = list(
        queryset.annotate(year=ExtractYear("reported_at")).values("year")
        .annotate(
            total=Count("id"),
            category_present=Count("id", filter=~Q(category="")),
            sub_category_present=Count("id", filter=~Q(sub_category="")),
            analytical_category_present=Count("id", filter=~Q(category="") | (~Q(sub_category="") & Q(category=""))),
            station_present=Count("id", filter=~Q(police_station="")),
            coordinate_present=Count("id", filter=Q(longitude__isnull=False, latitude__isnull=False)),
        ).order_by("year")
    )
    for row in yearly:
        row["category_pct"] = round(row["category_present"] / row["total"] * 100, 1) if row["total"] else 0
        row["sub_category_pct"] = round(row["sub_category_present"] / row["total"] * 100, 1) if row["total"] else 0
        row["analytical_category_pct"] = round(
            row["analytical_category_present"] / row["total"] * 100, 1
        ) if row["total"] else 0
        row["station_pct"] = round(row["station_present"] / row["total"] * 100, 1) if row["total"] else 0
        row["coordinate_pct"] = round(row["coordinate_present"] / row["total"] * 100, 1) if row["total"] else 0

    by_source = []
    for source, label in Incident.SourceType.choices:
        source_qs = queryset.filter(source_type=source)
        source_total = source_qs.count()
        by_source.append({
            "source_type": source, "label": label, "total": source_total,
            "category_pct": round(source_qs.exclude(category="").count() / source_total * 100, 1) if source_total else 0,
            "analytical_category_pct": round(classified_incident_count(source_qs) / source_total * 100, 1) if source_total else 0,
            "coordinate_pct": round(source_qs.filter(longitude__isnull=False, latitude__isnull=False).count() / source_total * 100, 1) if source_total else 0,
            "station_pct": round(source_qs.exclude(police_station="").count() / source_total * 100, 1) if source_total else 0,
        })

    duplicate_event_ids = list(
        queryset.values("event_id").annotate(total=Count("id"))
        .filter(total__gt=1).order_by("-total")[:20]
    )
    station_variants = list(
        queryset.exclude(police_station="").annotate(normalized=Lower("police_station"))
        .values("normalized").annotate(total=Count("id"), variants=Count("police_station", distinct=True))
        .filter(variants__gt=1).order_by("-total")[:20]
    )
    return {
        "total": total, "coordinate": coordinate, "metrics": metrics,
        "yearly": yearly, "by_source": by_source,
        "duplicate_event_ids": duplicate_event_ids, "station_variants": station_variants,
        "ugandan_bounds": UGANDA_BOUNDS,
    }


def station_profile_payload(queryset, station: str, include_map: bool = True):
    qs = queryset.filter(police_station=station)
    total = qs.count()
    coord = _coordinate_quality(qs)
    status = count_series(qs, "event_status", 12)
    closed = sum(row["total"] for row in status if row["event_status"].strip().upper() in CLOSED_STATUSES)
    map_points = _map_points(qs, 5000) if include_map else []
    return {
        "station": station,
        "kpis": {
            "total": total, "mapped": coord["valid"],
            "mapped_pct": round(coord["valid"] / total * 100, 1) if total else 0,
            "closed": closed, "closed_pct": round(closed / total * 100, 1) if total else 0,
            "categories": distinct_analytical_categories(qs),
        },
        "by_category": count_series(qs, "category", 15), "by_status": status,
        "by_source": count_series(qs, "source_type", 10), "by_month": _monthly_series(qs),
        "time": _time_patterns(qs, category_limit=4),
        "branches": count_series(qs, "governing_branch", 12),
        "locations": count_series(qs, "incident_location", 15),
        "recent": [
            {**row, "category": row[ANALYTICAL_CATEGORY_FIELD]}
            for row in with_analytical_category(qs).values(
                "id", "event_id", "reported_at", ANALYTICAL_CATEGORY_FIELD, "incident_location", "event_status"
            )[:20]
        ],
        "map_points": map_points,
        "map_metadata": map_points_metadata(qs, len(map_points)) if include_map else {},
    }


def category_profile_payload(queryset, category: str, include_map: bool = True):
    qs = with_analytical_category(queryset).filter(analytical_category=category)
    total = qs.count()
    coord = _coordinate_quality(qs)
    map_points = _map_points(qs, 5000) if include_map else []
    return {
        "category": category,
        "kpis": {
            "total": total, "mapped": coord["valid"],
            "mapped_pct": round(coord["valid"] / total * 100, 1) if total else 0,
            "stations": qs.exclude(police_station="").values("police_station").distinct().count(),
            "sub_categories": qs.exclude(sub_category="").values("sub_category").distinct().count(),
        },
        "by_station": count_series(qs, "police_station", 15),
        "by_sub_category": count_series(qs, "sub_category", 15),
        "by_status": count_series(qs, "event_status", 12),
        "by_source": count_series(qs, "source_type", 10),
        "by_month": _monthly_series(qs), "time": _time_patterns(qs, category_limit=0),
        "locations": count_series(qs, "incident_location", 15),
        "recent": list(qs.values("id", "event_id", "reported_at", "police_station", "incident_location", "event_status")[:20]),
        "map_points": map_points,
        "map_metadata": map_points_metadata(qs, len(map_points)) if include_map else {},
    }


def mappable_incidents(queryset):
    """Return incidents with usable coordinates inside the operational Uganda map boundary."""
    return queryset.filter(
        longitude__isnull=False,
        latitude__isnull=False,
        longitude__gte=UGANDA_BOUNDS["min_lon"],
        longitude__lte=UGANDA_BOUNDS["max_lon"],
        latitude__gte=UGANDA_BOUNDS["min_lat"],
        latitude__lte=UGANDA_BOUNDS["max_lat"],
    ).exclude(longitude=0, latitude=0)


def _map_category(row):
    """Use the platform-wide Category resolution rule for map payloads."""
    return resolve_category(row.get("category"), row.get("sub_category"))


def _map_points(queryset, limit=50000):
    rows = list(
        mappable_incidents(queryset)
        .values(
            "id", "event_id", "source_type", "origin", "reported_at", "incident_location",
            "case_nature", "category", "sub_category", "reporting_type",
            "governing_branch", "police_station", "event_status", "longitude", "latitude",
            "camera_id", "detection_label", "confidence",
        ).order_by("-reported_at")[:limit]
    )
    for row in rows:
        row["map_category"] = _map_category(row)
        row["category_key"] = category_colour_key(row["map_category"])
        row["category_colour"] = category_colour(row["map_category"])
    return rows


def map_points_payload(queryset, limit=50000):
    """Public, bounded map projection kept separate from cached analytical summaries."""
    return _map_points(queryset, limit)


def map_points_metadata(queryset, returned_count):
    """Explain coordinate coverage so administrators know what the map represents."""
    filtered_total = queryset.count()
    mapped_total = mappable_incidents(queryset).count()
    return {
        "filtered_total": filtered_total,
        "mapped_total": mapped_total,
        "unmapped_or_invalid_total": max(filtered_total - mapped_total, 0),
        "returned_total": returned_count,
        "truncated": mapped_total > returned_count,
        "bounds": UGANDA_BOUNDS,
    }



def _decision_support(queryset):
    """Dataset-relative operational comparison that remains meaningful for historical data."""
    dates = queryset.aggregate(first=Min("reported_at"), latest=Max("reported_at"))
    latest = dates["latest"]
    if latest is None:
        return {
            "first_date": None, "latest_date": None, "first_date_label": "", "latest_date_label": "", "current_30": 0, "previous_30": 0,
            "change_pct": 0, "change_direction": "flat", "daily_labels": [],
            "daily_values": [], "rolling_average": [], "aging": [],
            "field_station_80_count": 0, "field_station_total": 0, "top_momentum": [],
        }

    current_start = latest - timedelta(days=29)
    previous_end = current_start - timedelta(microseconds=1)
    previous_start = previous_end - timedelta(days=29)
    current_30 = queryset.filter(reported_at__gte=current_start, reported_at__lte=latest).count()
    previous_30 = queryset.filter(reported_at__gte=previous_start, reported_at__lte=previous_end).count()
    if previous_30:
        change_pct = round((current_30 - previous_30) / previous_30 * 100, 1)
    else:
        change_pct = 100.0 if current_30 else 0.0

    daily_start = latest - timedelta(days=89)
    daily_rows = list(
        queryset.filter(reported_at__gte=daily_start, reported_at__lte=latest)
        .annotate(day=TruncDate("reported_at"))
        .values("day").annotate(total=Count("id")).order_by("day")
    )
    daily_lookup = {row["day"]: row["total"] for row in daily_rows if row["day"]}
    labels, values, rolling = [], [], []
    cursor = daily_start.date()
    end_date = latest.date()
    while cursor <= end_date:
        labels.append(cursor.isoformat())
        values.append(daily_lookup.get(cursor, 0))
        window = values[max(0, len(values) - 7):]
        rolling.append(round(sum(window) / len(window), 1))
        cursor += timedelta(days=1)

    unresolved = queryset.exclude(event_status__in=["Closed", "CLOSED", "Fed Back", "FED BACK", "Delivered", "DELIVERED"])
    age_ranges = [
        ("0-1 day", 0, 1), ("2-3 days", 1, 3), ("4-7 days", 3, 7),
        ("8-30 days", 7, 30), ("Over 30 days", 30, None),
    ]
    aging = []
    for label, min_days, max_days in age_ranges:
        upper = latest - timedelta(days=min_days)
        bucket = unresolved.filter(reported_at__lt=upper) if min_days else unresolved.filter(reported_at__lte=upper)
        if max_days is not None:
            lower = latest - timedelta(days=max_days)
            bucket = bucket.filter(reported_at__gte=lower)
        aging.append({"label": label, "total": bucket.count()})

    field_rows = count_series(hotspot_queryset(queryset, include_command_center=False), "police_station", 500)
    field_total = sum(row["total"] for row in field_rows)
    cumulative = 0
    station_80_count = 0
    for row in field_rows:
        cumulative += row["total"]
        station_80_count += 1
        if field_total and cumulative / field_total >= 0.8:
            break

    current_90_start = latest - timedelta(days=89)
    previous_90_end = current_90_start - timedelta(microseconds=1)
    previous_90_start = previous_90_end - timedelta(days=89)
    current_categories = {
        row["category"]: row["total"] for row in count_series(
            queryset.filter(reported_at__gte=current_90_start, reported_at__lte=latest), "category", 200
        )
    }
    previous_categories = {
        row["category"]: row["total"] for row in count_series(
            queryset.filter(reported_at__gte=previous_90_start, reported_at__lte=previous_90_end), "category", 200
        )
    }
    momentum = []
    for category, current_total in current_categories.items():
        previous_total = previous_categories.get(category, 0)
        delta = current_total - previous_total
        pct = round(delta / previous_total * 100, 1) if previous_total else (100.0 if current_total else 0.0)
        momentum.append({
            "category": category, "current": current_total, "previous": previous_total,
            "delta": delta, "change_pct": pct,
        })
    momentum.sort(key=lambda row: (row["delta"], row["current"]), reverse=True)

    return {
        "first_date": dates["first"], "latest_date": latest,
        "first_date_label": timezone.localtime(dates["first"]).strftime("%d %b %Y") if dates["first"] else "",
        "latest_date_label": timezone.localtime(latest).strftime("%d %b %Y %H:%M"),
        "current_30": current_30, "previous_30": previous_30, "change_pct": change_pct,
        "change_direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
        "daily_labels": labels, "daily_values": values, "rolling_average": rolling,
        "aging": aging, "field_station_80_count": station_80_count,
        "field_station_total": len(field_rows), "top_momentum": momentum[:8],
    }


def _station_pareto(queryset):
    rows = count_series(hotspot_queryset(queryset, include_command_center=False), "police_station", 200)
    total = sum(row["total"] for row in rows)
    cumulative = 0
    result = []
    for row in rows[:25]:
        cumulative += row["total"]
        result.append({
            "police_station": row["police_station"],
            "total": row["total"],
            "cumulative_pct": round(cumulative / total * 100, 1) if total else 0,
        })
    return result

def dashboard_payload(queryset, include_map: bool = True):
    total = queryset.count()
    coordinate = _coordinate_quality(queryset)
    map_points = _map_points(queryset) if include_map else []
    streamed = queryset.filter(origin=Incident.Origin.STREAM).count()
    by_source = count_series(queryset, "source_type", 10)
    by_status = count_series(queryset, "event_status", 8)
    by_category = count_series(queryset, "category", 12)
    geographic = hotspot_queryset(queryset)
    by_hotspot = count_series(geographic, "police_station", 12)
    field_hotspots = count_series(hotspot_queryset(queryset, include_command_center=False), "police_station", 12)
    top_hotspot = by_hotspot[0] if by_hotspot else {"police_station": "No area", "total": 0}
    top_field = field_hotspots[0] if field_hotspots else {"police_station": "No field station", "total": 0}
    top_category = by_category[0] if by_category else {"category": "No category", "total": 0}
    top_hotspot_names = [row["police_station"] for row in field_hotspots[:5]]
    return {
        "kpis": {
            "total": total, "mapped": coordinate["valid"],
            "mapped_pct": round(coordinate["valid"] / total * 100, 1) if total else 0,
            "streamed": streamed,
            "top_hotspot": top_hotspot["police_station"], "top_hotspot_total": top_hotspot["total"],
            "top_hotspot_pct": round(top_hotspot["total"] / total * 100, 1) if total else 0,
            "top_field": top_field["police_station"], "top_field_total": top_field["total"],
            "top_category": top_category["category"], "top_category_total": top_category["total"],
            "top_category_pct": round(top_category["total"] / total * 100, 1) if total else 0,
        },
        "by_source": by_source, "by_status": by_status, "by_category": by_category,
        "by_hotspot": by_hotspot, "by_field_hotspot": field_hotspots,
        "by_year": _year_series(queryset), "by_month": _monthly_series(queryset),
        "hotspot_trend": _hotspot_trend(geographic, top_hotspot_names),
        "category_area": _category_area_join(queryset),
        "category_time": _category_time_analysis(queryset, category_limit=5),
        "time_patterns": _time_patterns(queryset, category_limit=4),
        "map_points": map_points,
        "map_metadata": map_points_metadata(queryset, len(map_points)) if include_map else {},
        "decision_support": _decision_support(queryset),
        "insights": operational_insights(queryset),
        "hotspot_exclusions": sorted(NON_GEOGRAPHIC_AREAS),
    }


def status_outcome_payload(queryset):
    closed_values = ["Closed", "CLOSED", "Fed Back", "FED BACK", "Delivered", "DELIVERED"]
    total = queryset.count()
    closed = queryset.filter(event_status__in=closed_values).count()
    unresolved_qs = queryset.exclude(event_status__in=closed_values)

    station_rows = list(
        queryset.exclude(police_station="").values("police_station")
        .annotate(total=Count("id"), closed=Count("id", filter=Q(event_status__in=closed_values)))
        .order_by("-total")[:15]
    )
    for row in station_rows:
        row["closed_pct"] = round(row["closed"] / row["total"] * 100, 1) if row["total"] else 0

    category_rows = list(
        with_analytical_category(queryset).values(ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"), closed=Count("id", filter=Q(event_status__in=closed_values)))
        .order_by("-total")[:15]
    )
    for row in category_rows:
        row["category"] = row.pop(ANALYTICAL_CATEGORY_FIELD)
    for row in category_rows:
        row["closed_pct"] = round(row["closed"] / row["total"] * 100, 1) if row["total"] else 0

    return {
        "kpis": {
            "total": total,
            "closed": closed,
            "closed_pct": round(closed / total * 100, 1) if total else 0,
            "unresolved": total - closed,
            "outcome_present": queryset.exclude(processing_result="").count(),
            "feedback_present": queryset.exclude(feedback_content="").count(),
        },
        "by_status": count_series(queryset, "event_status", 15),
        "reporting_types": count_series(queryset, "reporting_type", 12),
        "station_closure": station_rows,
        "category_closure": category_rows,
        "aging": _decision_support(queryset)["aging"],
        "old_unresolved": [
            {**row, "category": row[ANALYTICAL_CATEGORY_FIELD]}
            for row in with_analytical_category(unresolved_qs).values(
                "event_id", "reported_at", ANALYTICAL_CATEGORY_FIELD,
                "police_station", "event_status", "incident_location"
            ).order_by("reported_at")[:30]
        ],
    }


def _canonical_category_key(value):
    """Backward-compatible alias for the shared stable Category colour key."""
    return category_colour_key(value)


def map_report_payload(queryset, include_map: bool = True):
    """Build the reconciled payload for the interactive GIS map analytics report."""
    total = queryset.count()
    mapped_qs = mappable_incidents(queryset)
    mapped = mapped_qs.count()
    unmapped = max(total - mapped, 0)
    mapped_pct = round(mapped / total * 100, 1) if total else 0

    category_totals = list(
        with_analytical_category(queryset)
        .values(ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"), latest=Max("reported_at"))
        .order_by("-total", ANALYTICAL_CATEGORY_FIELD)
    )
    mapped_totals = {
        row[ANALYTICAL_CATEGORY_FIELD]: row["mapped"]
        for row in (
            with_analytical_category(mapped_qs)
            .values(ANALYTICAL_CATEGORY_FIELD)
            .annotate(mapped=Count("id"))
        )
    }

    top_station_by_category = {}
    station_rows = (
        with_analytical_category(mapped_qs)
        .exclude(police_station="")
        .values(ANALYTICAL_CATEGORY_FIELD, "police_station")
        .annotate(total=Count("id"))
        .order_by(ANALYTICAL_CATEGORY_FIELD, "-total", "police_station")
    )
    for row in station_rows:
        category = row[ANALYTICAL_CATEGORY_FIELD]
        if category not in top_station_by_category:
            top_station_by_category[category] = {
                "station": row["police_station"],
                "total": row["total"],
            }

    category_layers = []
    for row in category_totals:
        category = row[ANALYTICAL_CATEGORY_FIELD]
        category_total = row["total"]
        category_mapped = mapped_totals.get(category, 0)
        station = top_station_by_category.get(category, {"station": "No mapped station", "total": 0})
        category_layers.append({
            "category": category,
            "category_key": category_colour_key(category),
            "category_colour": category_colour(category),
            "total": category_total,
            "mapped": category_mapped,
            "unmapped": max(category_total - category_mapped, 0),
            "coverage_pct": round(category_mapped / category_total * 100, 1) if category_total else 0,
            "mapped_share_pct": round(category_mapped / mapped * 100, 1) if mapped else 0,
            "latest": row["latest"],
            "top_station": station["station"],
            "top_station_total": station["total"],
        })
    category_layers.sort(key=lambda item: (-item["mapped"], -item["total"], item["category"]))

    layer_by_key = {_canonical_category_key(row["category"]): row for row in category_layers}
    priority_layers = []
    used = set()
    for preferred in MAP_REPORT_PRIORITY_CATEGORIES:
        key = _canonical_category_key(preferred)
        layer = layer_by_key.get(key)
        if layer and layer["mapped"]:
            priority_layers.append(layer)
            used.add(key)
    for layer in category_layers:
        key = _canonical_category_key(layer["category"])
        if layer["mapped"] and key not in used:
            priority_layers.append(layer)
            used.add(key)
        if len(priority_layers) >= 12:
            break
    priority_layers = [dict(layer, chapter=index + 1) for index, layer in enumerate(priority_layers)]

    with_location = queryset.exclude(incident_location="")
    with_location_count = with_location.count()
    top_locations = count_series(with_location, "incident_location", 20)
    top_names = [row["incident_location"] for row in top_locations[:10]]
    location_categories = [
        row["category"]
        for row in count_series(with_location.filter(incident_location__in=top_names), "category", 6)
    ]
    category_location_rows = list(
        with_analytical_category(with_location)
        .filter(incident_location__in=top_names, analytical_category__in=location_categories)
        .values("incident_location", ANALYTICAL_CATEGORY_FIELD)
        .annotate(total=Count("id"))
    )
    location_lookup = {
        (row["incident_location"], row[ANALYTICAL_CATEGORY_FIELD]): row["total"]
        for row in category_location_rows
    }
    category_location = {
        "locations": top_names,
        "categories": location_categories,
        "datasets": [
            {
                "category": category,
                "values": [location_lookup.get((location, category), 0) for location in top_names],
            }
            for category in location_categories
        ],
    }
    multi_category = list(
        with_analytical_category(with_location)
        .values("incident_location")
        .annotate(total=Count("id"), categories=Count(ANALYTICAL_CATEGORY_FIELD, distinct=True))
        .filter(total__gt=1, categories__gt=1)
        .order_by("-total")[:25]
    )

    top_mapped_category = category_layers[0] if category_layers else {
        "category": "No mapped category", "mapped": 0, "mapped_share_pct": 0,
        "coverage_pct": 0, "top_station": "No mapped station",
    }
    top_mapped_stations = count_series(mapped_qs, "police_station", 15)
    top_mapped_station = top_mapped_stations[0] if top_mapped_stations else {
        "police_station": "No mapped station", "total": 0,
    }
    top_five_mapped = sum(row["mapped"] for row in category_layers[:5])
    top_five_share = round(top_five_mapped / mapped * 100, 1) if mapped else 0
    coverage_grade = "Strong" if mapped_pct >= 80 else "Moderate" if mapped_pct >= 50 else "Limited"

    chart_layers = category_layers[:18]
    map_points = _map_points(queryset, 50000) if include_map else []
    return {
        "kpis": {
            "total": total,
            "mapped": mapped,
            "unmapped": unmapped,
            "mapped_pct": mapped_pct,
            "coverage_grade": coverage_grade,
            "mapped_categories": sum(1 for row in category_layers if row["mapped"]),
            "all_categories": len(category_layers),
            "mapped_stations": mapped_qs.exclude(police_station="").order_by().values("police_station").distinct().count(),
            "with_location": with_location_count,
            "location_pct": round(with_location_count / total * 100, 1) if total else 0,
            "repeat_locations": with_location.values("incident_location").annotate(total=Count("id")).filter(total__gt=1).count(),
            "top_category": top_mapped_category["category"],
            "top_category_mapped": top_mapped_category["mapped"],
            "top_category_share_pct": top_mapped_category["mapped_share_pct"],
            "top_station": top_mapped_station["police_station"],
            "top_station_mapped": top_mapped_station["total"],
            "top_five_share_pct": top_five_share,
        },
        "priority_layers": priority_layers,
        "category_layers": category_layers,
        "coordinate_quality": _coordinate_quality(queryset),
        "category_coverage": {
            "labels": [row["category"] for row in chart_layers],
            "mapped": [row["mapped"] for row in chart_layers],
            "unmapped": [row["unmapped"] for row in chart_layers],
        },
        "top_mapped_stations": top_mapped_stations,
        "top_locations": top_locations,
        "category_location": category_location,
        "multi_category": multi_category,
        "locations_by_station": count_series(with_location, "police_station", 15),
        "observations": [
            {
                "label": "Coordinate coverage",
                "value": f"{mapped_pct}%",
                "detail": f"{mapped:,} of {total:,} filtered incidents can be placed on the operational map.",
                "severity": "good" if mapped_pct >= 80 else "warning" if mapped_pct >= 50 else "risk",
            },
            {
                "label": "Category concentration",
                "value": f"{top_five_share}%",
                "detail": "Share of mapped coordinates represented by the five largest categories.",
                "severity": "neutral",
            },
            {
                "label": "Leading mapped category",
                "value": top_mapped_category["category"],
                "detail": f"{top_mapped_category['mapped']:,} mapped incidents ({top_mapped_category['mapped_share_pct']}% of mapped records).",
                "severity": "neutral",
            },
            {
                "label": "Leading mapped station",
                "value": top_mapped_station["police_station"],
                "detail": f"{top_mapped_station['total']:,} mapped incidents in the filtered selection.",
                "severity": "neutral",
            },
        ],
        "map_points": map_points,
        "map_metadata": map_points_metadata(queryset, len(map_points)) if include_map else {},
    }


def location_intelligence_payload(queryset, include_map: bool = True):
    """Backward-compatible alias for older imports and bookmarks."""
    return map_report_payload(queryset, include_map=include_map)


def _linear_forecast(monthly, periods=3):
    if len(monthly) < 2:
        return {"labels": [item["month"] for item in monthly], "actual": [item["total"] for item in monthly], "baseline": [], "forecast": []}
    window = monthly[-12:]
    y = [float(item["total"]) for item in window]
    x = list(range(len(y)))
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    slope = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(x))) / denominator if denominator else 0
    intercept = y_mean - slope * x_mean

    labels = [item["month"] for item in monthly]
    actual = [item["total"] for item in monthly]
    baseline = []
    for index in range(len(actual)):
        prior = actual[max(0, index - 3):index]
        baseline.append(round(sum(prior) / len(prior), 1) if prior else None)

    latest_date = datetime.strptime(monthly[-1]["month"], "%Y-%m-%d").date()
    forecast_values = [None] * len(actual)
    forecast_labels = []
    for offset in range(1, periods + 1):
        month_number = latest_date.month - 1 + offset
        year = latest_date.year + month_number // 12
        month = month_number % 12 + 1
        forecast_labels.append(f"{year:04d}-{month:02d}-01")
        projected = max(0, round(intercept + slope * (len(y) - 1 + offset)))
        forecast_values.append(projected)
    labels.extend(forecast_labels)
    actual.extend([None] * periods)
    baseline.extend([None] * periods)
    return {"labels": labels, "actual": actual, "baseline": baseline, "forecast": forecast_values}


def _description_themes(queryset, limit=20):
    import re
    from collections import Counter

    stopwords = {
        "the", "and", "was", "were", "that", "this", "with", "from", "have", "has", "had", "for", "into",
        "there", "they", "their", "them", "then", "when", "where", "which", "what", "who", "been", "being",
        "reported", "caller", "incident", "police", "station", "command", "center", "centre", "room", "near",
        "road", "area", "case", "said", "also", "after", "before", "about", "over", "under", "upon", "while",
    }
    counter = Counter()
    descriptions = queryset.exclude(description="").values_list("description", flat=True).order_by("-reported_at")[:20000]
    for description in descriptions.iterator(chunk_size=1000):
        words = re.findall(r"[A-Za-z]{4,}", description.lower())
        counter.update(word for word in words if word not in stopwords)
    return [{"term": term, "total": total} for term, total in counter.most_common(limit)]


def predictive_intelligence_payload(queryset):
    monthly = _monthly_series(queryset)
    forecast = _linear_forecast(monthly, periods=3)
    anomalies = []
    totals = [item["total"] for item in monthly]
    for index in range(3, len(monthly)):
        average = sum(totals[index - 3:index]) / 3
        if not average:
            continue
        change = round((totals[index] - average) / average * 100, 1)
        if abs(change) >= 25:
            anomalies.append({
                "month": monthly[index]["month"],
                "total": totals[index],
                "baseline": round(average, 1),
                "change": change,
                "direction": "increase" if change > 0 else "decrease",
            })
    anomalies = sorted(anomalies, key=lambda row: abs(row["change"]), reverse=True)[:20]
    return {
        "kpis": {
            "months": len(monthly),
            "anomalies": len(anomalies),
            "latest_total": monthly[-1]["total"] if monthly else 0,
            "forecast_next": next((value for value in forecast["forecast"] if value is not None), 0),
        },
        "forecast": forecast,
        "anomalies": anomalies,
        "themes": _description_themes(queryset),
        "by_category": count_series(queryset, "category", 12),
    }
