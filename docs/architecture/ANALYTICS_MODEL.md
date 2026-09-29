# Analytics Model

## Decision-support anchor

Historical comparisons are anchored to the latest incident in the current filter selection, not the server date. This prevents a 2020-2024 dataset from showing misleading zero values for the current calendar month.

## New operational measures

### Recent-period movement

- Latest 30-day incident volume
- Preceding 30-day volume
- Percentage movement between the periods
- Daily volume for the latest 90 reporting days
- Seven-day rolling average

### Unresolved aging

Open incidents are grouped into:

- 0-1 day
- 2-3 days
- 4-7 days
- 8-30 days
- Over 30 days

Aging is calculated relative to the latest filtered incident date.

### Category momentum

The latest 90 reporting days are compared with the preceding 90 days. Categories are ranked by absolute change and exposed on the command overview for rapid administrative review.

### Field-station concentration

A Pareto series shows incident volume by field station and cumulative share. The command overview also reports how many field stations account for 80% of field workload.

## Existing analytical coverage

- Category-coloured clustered map and heatmap
- Area/category matrix
- Category trends and seasonality
- Hour/day heatmap
- Command Center and dispatch flows
- Closure rate and unresolved follow-up
- Repeat-location intelligence
- Data completeness and coordinate validity
- Baseline anomaly detection and simple projection

## Caching model

Unfiltered dashboard and data-quality payloads are cached. A source-state token based on row count and latest creation time changes the cache key when data changes. Durable `AnalyticsSnapshot` records provide a fallback and an auditable generation timestamp.

## GIS map report model

The GIS report is built from one filtered incident queryset so every KPI, map, table and chart reconciles.

### Report hierarchy

1. Overall mapped distribution
2. Selectable exact-Category layers
3. Category coordinate coverage comparison
4. Repeat-location and multi-Category concentration
5. Coordinate-quality interpretation and operational actions

### Category-layer measures

For each resolved Category, the report calculates:

- total filtered incidents;
- valid mapped coordinates;
- unmapped or invalid coordinates;
- coordinate coverage percentage;
- share of all mapped coordinates;
- latest reported incident time;
- leading mapped station and its mapped count.

Category is used first. Sub-Category fills the analytical Category only when Category is blank. Exact Category labels are retained in the atlas and layer controls.

### Map performance

The overall map and selected Category map use separate lazy requests to the bounded map API. The selected Category layer is fetched only when opened. Both maps use marker clustering and canvas-preferred Leaflet rendering.
