#!/usr/bin/env python3
"""
System Fixes Validation Script

Validates that all 4 critical system fixes are working correctly.
Run after deploying fixes to verify system stability.

Usage:
    # From project root with venv activated:
    source venv/bin/activate
    python scripts/validate_system_fixes.py

    # Or use venv python directly:
    venv/bin/python scripts/validate_system_fixes.py

Exit Codes:
    0 - All validations passed
    1 - One or more validations failed
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def validate_datetime_serialization():
    """Validate datetime JSON serialization fix

    Tests that RunEvent.model_dump(mode='json') properly serializes datetime objects.
    """
    print("✓ Testing datetime JSON serialization...")

    try:
        from AICrews.schemas.stats import RunEvent, RunEventType

        event = RunEvent(
            run_id="test",
            event_type=RunEventType.TASK_STATE,
            timestamp=datetime.now(),
            payload={"status": "test"}
        )

        # Test serialization
        serialized = event.model_dump(mode='json')

        # Verify timestamp is a string (ISO format)
        if not isinstance(serialized['timestamp'], str):
            print(f"  ❌ Datetime serialization: FAIL - timestamp is {type(serialized['timestamp'])}, expected str")
            return False

        # Verify it's a valid ISO format
        try:
            datetime.fromisoformat(serialized['timestamp'].replace('Z', '+00:00'))
        except ValueError as e:
            print(f"  ❌ Datetime serialization: FAIL - invalid ISO format: {e}")
            return False

        print("  ✅ Datetime serialization: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Datetime serialization: FAIL - {e}")
        return False


def validate_redis_sync():
    """Validate Redis sync method

    Tests that RedisManager has incr_sync() method for synchronous operations.
    """
    print("✓ Testing Redis sync method...")

    try:
        from AICrews.infrastructure.cache.redis_manager import RedisManager

        manager = RedisManager()

        # Check method exists
        if not hasattr(manager, 'incr_sync'):
            print("  ❌ Redis sync: FAIL - incr_sync method not found")
            return False

        # Check method signature
        import inspect
        sig = inspect.signature(manager.incr_sync)
        params = list(sig.parameters.keys())

        # Expect: key, amount=1, ttl=60
        if 'key' not in params:
            print("  ❌ Redis sync: FAIL - incr_sync missing 'key' parameter")
            return False

        print("  ✅ Redis sync method: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Redis sync: FAIL - {e}")
        return False


def validate_ticker_normalization():
    """Validate ticker normalization

    Tests that normalize_ticker() properly handles HK/CN/US stock formats.
    """
    print("✓ Testing ticker normalization...")

    try:
        from AICrews.utils.ticker_utils import normalize_ticker, validate_ticker

        tests = [
            ("0700", "0700.HK", "HK stock (4-digit)"),
            ("600000", "600000.SS", "Shanghai stock (starts with 6)"),
            ("000001", "000001.SZ", "Shenzhen stock (starts with 0)"),
            ("300001", "300001.SZ", "Shenzhen stock (starts with 3)"),
            ("AAPL", "AAPL", "US stock (alphabetic)"),
            ("0700.HK", "0700.HK", "Already normalized HK"),
            ("600000.SS", "600000.SS", "Already normalized Shanghai"),
        ]

        all_pass = True
        for input_ticker, expected, description in tests:
            result = normalize_ticker(input_ticker)
            if result != expected:
                print(f"  ❌ {description}: FAIL - expected {expected}, got {result}")
                all_pass = False
            else:
                print(f"  ✅ {description}: PASS")

        # Test validation
        is_valid, error = validate_ticker("AAPL")
        if not is_valid:
            print(f"  ❌ Ticker validation: FAIL - {error}")
            all_pass = False
        else:
            print("  ✅ Ticker validation: PASS")

        # Test invalid ticker
        is_valid, error = validate_ticker("")
        if is_valid:
            print("  ❌ Ticker validation (empty): FAIL - should reject empty ticker")
            all_pass = False
        else:
            print("  ✅ Ticker validation (empty): PASS")

        return all_pass

    except Exception as e:
        print(f"  ❌ Ticker normalization: FAIL - {e}")
        return False


def validate_expression_validation():
    """Validate expression tool error messages

    Tests that ExpressionEngine provides helpful error messages for unsupported variables.
    """
    print("✓ Testing expression tool validation...")

    try:
        from AICrews.tools.expression_tools import ExpressionEngine

        engine = ExpressionEngine()

        # Test 1: Unsupported variable CURRENT_PRICE
        is_valid, error = engine.validate_formula("CURRENT_PRICE > 100")

        if is_valid:
            print("  ❌ Expression validation: FAIL - should reject CURRENT_PRICE")
            return False

        if "CURRENT_PRICE" not in error:
            print(f"  ❌ Expression validation: FAIL - error doesn't mention CURRENT_PRICE: {error}")
            return False

        if "Use CLOSE" not in error:
            print(f"  ❌ Expression validation: FAIL - error doesn't suggest CLOSE: {error}")
            return False

        print("  ✅ Expression validation (CURRENT_PRICE): PASS")

        # Test 2: Unsupported variable PRICE
        is_valid, error = engine.validate_formula("PRICE > 100")

        if is_valid:
            print("  ❌ Expression validation: FAIL - should reject PRICE")
            return False

        if "PRICE" not in error or "Use CLOSE" not in error:
            print(f"  ❌ Expression validation: FAIL - unhelpful error for PRICE: {error}")
            return False

        print("  ✅ Expression validation (PRICE): PASS")

        # Test 3: Valid formula should pass
        is_valid, error = engine.validate_formula("CLOSE > 100")

        if not is_valid:
            print(f"  ❌ Expression validation: FAIL - should accept valid formula: {error}")
            return False

        print("  ✅ Expression validation (valid formula): PASS")

        # Test 4: Natural language should fail with helpful message
        is_valid, error = engine.validate_formula("Dip Buy Check")

        if is_valid:
            print("  ❌ Expression validation: FAIL - should reject natural language")
            return False

        if "boolean expression" not in error.lower() and "syntax" not in error.lower():
            print(f"  ❌ Expression validation: FAIL - error should mention boolean expression/syntax: {error}")
            return False

        print("  ✅ Expression validation (natural language): PASS")

        return True

    except Exception as e:
        print(f"  ❌ Expression validation: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation checks"""
    print("\n" + "="*60)
    print("System Fixes Validation - 2025-12-31")
    print("="*60 + "\n")

    results = []

    # Run validations
    print("Running validation checks...\n")

    results.append(await validate_datetime_serialization())
    print()

    results.append(validate_redis_sync())
    print()

    results.append(validate_ticker_normalization())
    print()

    results.append(validate_expression_validation())
    print()

    # Summary
    print("="*60)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} validation checks PASSED")
        print("="*60)
        return 0
    else:
        print(f"❌ {total - passed} of {total} validation check(s) FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
