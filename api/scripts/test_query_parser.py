"""Test script for query parser."""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import query_parser


def test_query_parser():
    """Test various query parsing scenarios."""
    test_cases = [
        # (query, explicit_make, explicit_model, expected_make, expected_model, description)
        ("nissan 350z", None, None, "nissan", "350z", "Parse make and model"),
        ("nissan", None, None, "nissan", None, "Parse make only"),
        ("toyota supra", None, None, "toyota", "supra", "Parse toyota supra"),
        ("ford mustang gt", None, None, "ford", "mustang gt", "Multi-word model"),
        ("honda civic 2020", None, None, "honda", "civic 2020", "Model with year"),
        ("chevrolet camaro", None, None, "chevrolet", "camaro", "Full make name"),
        ("chevy camaro", None, None, "chevrolet", "camaro", "Make alias (chevy->chevrolet)"),
        ("land rover defender", None, None, "land rover", "defender", "Two-word make"),
        ("alfa romeo giulia", None, None, "alfa romeo", "giulia", "Two-word make (alfa romeo)"),
        ("random query", None, None, None, None, "Unknown make - graceful fallback"),
        ("ford mustang", "nissan", None, "nissan", "mustang", "PRIORITY: Explicit make overrides parsed"),
        ("nissan 350z", "toyota", None, "toyota", "350z", "PRIORITY: Explicit make overrides, parse model"),
        ("nissan 350z", "toyota", "supra", "toyota", "supra", "PRIORITY: Both explicit override all"),
        ("nissan 350z", None, "supra", "nissan", "supra", "PRIORITY: Explicit model overrides parsed"),
    ]

    print("Testing query parser...\n")
    passed = 0
    failed = 0

    for query, explicit_make, explicit_model, expected_make, expected_model, description in test_cases:
        query_norm, parsed = query_parser.parse_query(query, explicit_make, explicit_model)
        actual_make = parsed.get("make")
        actual_model = parsed.get("model")

        success = actual_make == expected_make and actual_model == expected_model

        if success:
            print(f"[PASS] {description}")
            print(f"       '{query}' (make={explicit_make}, model={explicit_model})")
            print(f"       -> make={actual_make}, model={actual_model}")
            passed += 1
        else:
            print(f"[FAIL] {description}")
            print(f"       '{query}' (make={explicit_make}, model={explicit_model})")
            print(f"  Expected: make={expected_make}, model={expected_model}")
            print(f"  Got:      make={actual_make}, model={actual_model}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = test_query_parser()
    sys.exit(0 if success else 1)
