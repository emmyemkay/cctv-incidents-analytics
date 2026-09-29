# Operational Map Category Colour Rules

## Classification rule

The map resolves the displayed Category in this order:

1. Use `Category` when populated.
2. Use `Sub-Category` only when `Category` is blank.
3. Use `Uncategorised` when both are blank.

The original Category, Sub-Category and Case Nature values remain available in the incident record and exports.

## Colour identity rule

The Category name from the CSV is the colour identity.

- All records named `Breakings` use the same colour.
- All records named `Assaults` use the same colour.
- All records named `Traffic and Road Safety Act (Not categorised)` use the same colour.
- Different Category names receive different deterministic colours.
- Category names are not combined into broad families.

For colour matching only, the application normalizes:

- upper/lower case;
- repeated whitespace;
- harmless spaces immediately inside parentheses.

This means formatting variants such as `Breakings`, `BREAKINGS` and ` Breakings ` resolve to the same colour key while the original display value remains available.

## Stable colour generation

A deterministic hash of the normalized Category name generates the marker colour. The generated hue, saturation and lightness remain stable across:

- page reloads;
- date filters;
- stations and operational areas;
- different CSV files;
- historical imports;
- live WebSocket events.

`Uncategorised` uses a fixed light-slate colour.

The bundled datasets contain 52 resolved Category names. The current colour algorithm produces 52 distinct colours for those names with no collisions.

## Coordinate and legend behaviour

- Every valid Uganda coordinate is plotted as a category-coloured point.
- Clusters display a multi-colour ring based on the exact Categories inside them.
- The legend retains one row per normalized Category name.
- Each legend row shows the Category name, colour, mapped count and share of mapped incidents.
- Administrators can search, show all, show the top ten, clear or toggle an individual Category.
- Category and Sub-Category are not overwritten by the colour logic.
