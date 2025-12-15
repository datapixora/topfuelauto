"""
Query parser service for extracting structured vehicle filters from free-text queries.
"""
from typing import Dict, Any, Tuple


# Common vehicle makes (normalized to lowercase for matching)
KNOWN_MAKES = {
    "acura", "alfa romeo", "aston martin", "audi", "bentley", "bmw", "bugatti",
    "buick", "cadillac", "chevrolet", "chevy", "chrysler", "dodge", "ferrari",
    "fiat", "ford", "genesis", "gmc", "honda", "hyundai", "infiniti", "jaguar",
    "jeep", "kia", "lamborghini", "land rover", "lexus", "lincoln", "maserati",
    "mazda", "mclaren", "mercedes", "mercedes-benz", "mini", "mitsubishi",
    "nissan", "pagani", "porsche", "ram", "rolls-royce", "subaru", "suzuki",
    "tesla", "toyota", "volkswagen", "vw", "volvo",
}

# Make aliases for better matching
MAKE_ALIASES = {
    "chevy": "chevrolet",
    "vw": "volkswagen",
    "mercedes": "mercedes-benz",
    "benz": "mercedes-benz",
}


def normalize_make(make: str) -> str:
    """Normalize a make name, applying aliases."""
    make_lower = make.lower().strip()
    return MAKE_ALIASES.get(make_lower, make_lower)


def parse_query(
    q: str,
    explicit_make: str | None = None,
    explicit_model: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Parse a free-text query and extract structured filters.

    Args:
        q: The raw query string (e.g., "nissan 350z", "toyota supra 2020")
        explicit_make: Explicit make filter (takes precedence)
        explicit_model: Explicit model filter (takes precedence)

    Returns:
        Tuple of (query_normalized, parsed_filters)
        where parsed_filters = {"make": str|None, "model": str|None}
    """
    # Normalize the query
    query_normalized = " ".join(q.strip().lower().split())
    tokens = query_normalized.split()

    # If explicit filters are provided, use them and return
    if explicit_make and explicit_model:
        return query_normalized, {"make": explicit_make, "model": explicit_model}

    if not tokens:
        return query_normalized, {"make": explicit_make, "model": explicit_model}

    # Try to extract make from the beginning of the query
    parsed_make = explicit_make
    parsed_model = explicit_model
    remaining_tokens = tokens[:]

    if not explicit_make:
        # Try single-token make
        if tokens[0] in KNOWN_MAKES:
            parsed_make = normalize_make(tokens[0])
            remaining_tokens = tokens[1:]
        # Try two-token make (e.g., "land rover", "alfa romeo")
        elif len(tokens) >= 2:
            two_token = f"{tokens[0]} {tokens[1]}"
            if two_token in KNOWN_MAKES:
                parsed_make = normalize_make(two_token)
                remaining_tokens = tokens[2:]
    else:
        # If explicit make is provided, try to remove it from the query to get model
        # Try single-token make removal
        if tokens and tokens[0] in KNOWN_MAKES:
            remaining_tokens = tokens[1:]
        # Try two-token make removal (e.g., "land rover", "alfa romeo")
        elif len(tokens) >= 2:
            two_token = f"{tokens[0]} {tokens[1]}"
            if two_token in KNOWN_MAKES:
                remaining_tokens = tokens[2:]

    # If we have a make (explicit or parsed) and don't have explicit model, use remaining tokens as model
    if (parsed_make or explicit_make) and not explicit_model and remaining_tokens:
        parsed_model = " ".join(remaining_tokens)

    return query_normalized, {"make": parsed_make, "model": parsed_model}


def apply_parsed_filters(
    filters: Dict[str, Any],
    parsed_make: str | None,
    parsed_model: str | None,
) -> Dict[str, Any]:
    """
    Apply parsed make/model to filters, respecting explicit values.

    Args:
        filters: Existing filter dict
        parsed_make: Parsed make from query
        parsed_model: Parsed model from query

    Returns:
        Updated filters dict
    """
    updated_filters = filters.copy()

    # Only apply parsed values if not explicitly set
    if not updated_filters.get("make") and parsed_make:
        updated_filters["make"] = parsed_make

    if not updated_filters.get("model") and parsed_model:
        updated_filters["model"] = parsed_model

    return updated_filters
