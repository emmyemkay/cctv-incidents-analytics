from incidents.services.categories import (
    UNCATEGORISED_LABEL,
    category_colour,
    category_colour_key,
    resolve_category,
)


def test_resolve_category_uses_required_fallback_order():
    assert resolve_category(" Breakings ", "Thefts") == "Breakings"
    assert resolve_category("", " Domestic Violence ") == "Domestic Violence"
    assert resolve_category("", "") == UNCATEGORISED_LABEL


def test_harmless_case_and_spacing_variants_share_a_colour():
    variants = ["Breakings", "BREAKINGS", "  Breakings  "]

    assert len({category_colour_key(value) for value in variants}) == 1
    assert len({category_colour(value) for value in variants}) == 1


def test_different_exact_category_names_normally_have_different_colours():
    assert category_colour("Breakings") != category_colour("Robberies")
    assert category_colour("Uncategorised") == "#94a3b8"
