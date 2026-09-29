# GIS Map Analytics Report

## Purpose

The GIS Map Analytics Report reorganises geographic analysis into a clear report sequence while retaining interactive filtering. It was designed from the useful analytical pattern in the supplied GIS report: begin with overall incident distribution, then isolate important incident classes as separate map layers.

The implementation improves on static screenshots by keeping every map connected to the same filtered incident queryset and the same coordinate-validation rule.

## Route

```text
/analytics/map-report/
```

The former route below is preserved as a redirect:

```text
/analytics/locations/
```

## Report structure

### 1. Overall Incident Distribution

- Plots every valid coordinate in the current filtered selection.
- Uses the resolved Category for colour and legend identity.
- Supports points, heatmap and combined display modes.
- Shows mapped coverage, leading Category, leading station and the latest mapped incident.
- Keeps unmapped incidents in analytical totals but excludes them from visible geographic patterns.

### 2. Category Map Layers

- Presents priority layers inspired by the supplied GIS report, including traffic, breakings, shooting deaths, child-related offences, robberies, sex-related offences and theft where those categories exist.
- Completes the layer list with the highest-volume mapped Categories.
- Loads the selected Category map lazily through the existing bounded map API.
- Displays total, mapped, unmapped, coverage, mapped share, leading station and latest report time.
- Preserves exact Category names; it does not merge categories.

### 3. Category Coverage and Map Atlas

- Compares mapped and unmapped records by Category.
- Lists every resolved Category in one searchable atlas.
- Allows any Category to be opened immediately in the Category map workspace.
- Shows the leading mapped station for each Category.

### 4. Repeat Locations and Category Concentration

- Ranks recurring free-text incident locations.
- Compares the Category mix at the most repeated locations.
- Highlights locations associated with multiple Categories.
- Lists stations with the strongest location-detail coverage.

### 5. Conclusion and Operational Use

- Supports deployment planning, targeted Category analysis, coordinate-quality improvement and follow-up through trend and outcome pages.
- Explicitly warns users that weak coordinate coverage limits geographic conclusions.

## Coordinate rule

A record is mappable only when both coordinates are present, not `0,0`, and fall inside the configured Uganda operating bounds:

```text
Latitude:  -1.6 to 4.5
Longitude: 29.4 to 35.1
```

## Category rule

```text
Category populated
    -> use Category

Category empty and Sub-Category populated
    -> use Sub-Category as Category

Both empty
    -> Uncategorised
```

The same resolved Category is used by filters, map markers, legends, Category profiles and the map atlas.

## Main implementation files

```text
incidents/services/analytics.py
incidents/views.py
incidents/urls.py
incidents/templates/incidents/map_analytics_report.html
incidents/static/incidents/js/map-colors.js
incidents/static/incidents/js/analytics.js
incidents/static/incidents/js/map-report.js
incidents/static/incidents/css/app.css
```

## Performance

- Overall map points are loaded through `/api/v1/analytics/map-points/`.
- Category maps are requested only when a Category is selected.
- The API remains bounded at 50,000 points.
- Marker clustering and canvas-preferred Leaflet rendering reduce browser load.
- Summary payloads remain cacheable when global filters are not applied.
