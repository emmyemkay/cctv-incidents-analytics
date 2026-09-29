# Category Analytics Rule

The platform uses **Category** as the single analytical classification name. It preserves the source `Category`, `Sub-Category`, and `Case Nature` fields, but Case Nature is reference data only and does not drive analytical grouping.

1. Use `Category` when it is populated.
2. Use `Sub-Category` only when `Category` is blank.
3. Use `Uncategorised` when both fields are blank.

The derived Category is used by maps, map colours, category filters, category profiles, dashboard charts, hotspot matrices, trends, outcome analysis, incident lists and exports. The interface continues to call the field **Category**; it is never relabelled as Case Nature. Raw Category, Sub-Category, and Case Nature remain available for traceability.

For the bundled 36,076 records, 32,134 records have Category populated and 3,942 have both fields blank. No bundled record currently requires the Sub-Category fallback, but the rule protects future uploads and real-time events where Category may be blank and Sub-Category populated.

The historical `0011_backfill_case_nature` migration is retained only for migration-history compatibility. Current analytics do not use Case Nature as the primary classification.
