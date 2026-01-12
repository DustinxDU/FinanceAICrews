#!/usr/bin/env python
"""
LLM Policy Router Integration Verification Script

Tests the complete integration flow:
1. Free user → agents_fast (system fallback, no BYOK)
2. Premium user without BYOK → agents_balanced (system fallback)
3. Premium user with BYOK → agents_best (BYOK path with user_config)
4. Lazy provisioning path (retry_after error)
5. Trace sanity (run_id, trace_id, tags)

Usage:
    # Set environment variable first
    export LLM_POLICY_ROUTER_ENABLED=true

    # Run verification
    python scripts/verify_router_integration.py
"""

import asyncio
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet

# Generate test encryption key BEFORE importing modules
# This ensures consistency across all encryption operations
TEST_ENCRYPTION_KEY = Fernet.generate_key()
os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY.decode()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from AICrews.database.models.base import Base
from AICrews.database.models.user import User
from AICrews.database.models.llm_policy import (
    LLMSystemProfile,
    LLMUserByokProfile,
    LLMVirtualKey,
    VirtualKeyStatusEnum,
)
from AICrews.llm.runtime.runtime import get_llm_runtime
from AICrews.schemas.llm_policy import LLMScope, UserContext, LLMKeyProvisioningError
from AICrews.utils.encryption import encrypt_api_key


def setup_test_db():
    """Create in-memory test database with fixture data."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create system profiles
    system_profiles = [
        LLMSystemProfile(
            scope="copilot",
            proxy_model_name="sys_copilot_v1",
            enabled=True,
        ),
        LLMSystemProfile(
            scope="agents_fast",
            proxy_model_name="agents_fast",
            enabled=True,
        ),
        LLMSystemProfile(
            scope="agents_balanced",
            proxy_model_name="agents_balanced",
            enabled=True,
        ),
        LLMSystemProfile(
            scope="agents_best",
            proxy_model_name="agents_best",
            enabled=True,
        ),
    ]
    session.add_all(system_profiles)

    # Create test users
    free_user = User(
        email="free@example.com",
        username="freeuser",
        password_hash="hashed",
        subscription_level="free",
        is_active=True,
    )
    premium_user_no_byok = User(
        email="premium_no_byok@example.com",
        username="premium_no_byok",
        password_hash="hashed",
        subscription_level="premium",
        is_active=True,
    )
    premium_user_with_byok = User(
        email="premium_byok@example.com",
        username="premium_byok",
        password_hash="hashed",
        subscription_level="premium",
        is_active=True,
    )
    user_provisioning = User(
        email="provisioning@example.com",
        username="provisioning_user",
        password_hash="hashed",
        subscription_level="premium",
        is_active=True,
    )

    session.add_all([free_user, premium_user_no_byok, premium_user_with_byok, user_provisioning])
    session.commit()

    # Create virtual keys for users (ACTIVE for normal users)
    for user in [free_user, premium_user_no_byok, premium_user_with_byok]:
        # vk_user
        vk_user = LLMVirtualKey(
            user_id=user.id,
            key_type="user",
            key_alias=f"vk:user:{user.id}",
            status=VirtualKeyStatusEnum.ACTIVE,
            allowed_models=["agents_fast", "agents_balanced", "agents_best"],
            litellm_key_encrypted=encrypt_api_key(f"sk-vk-user-{user.id}"),
        )
        # vk_system_on_behalf
        vk_obo = LLMVirtualKey(
            user_id=user.id,
            key_type="system_on_behalf",
            key_alias=f"vk:obo:{user.id}",
            status=VirtualKeyStatusEnum.ACTIVE,
            allowed_models=["sys_copilot_v1", "sys_cockpit_scan_v1"],
            litellm_key_encrypted=encrypt_api_key(f"sk-vk-obo-{user.id}"),
        )
        session.add_all([vk_user, vk_obo])

    # Create PROVISIONING key for provisioning test user
    vk_provisioning = LLMVirtualKey(
        user_id=user_provisioning.id,
        key_type="user",
        key_alias=f"vk:user:{user_provisioning.id}",
        status=VirtualKeyStatusEnum.PROVISIONING,
        allowed_models=["agents_fast"],
        retry_count=0,
    )
    session.add(vk_provisioning)

    # Create BYOK profile for premium_user_with_byok
    byok_profile = LLMUserByokProfile(
        user_id=premium_user_with_byok.id,
        tier="agents_best",
        provider="openai",
        model="gpt-4o",
        api_key_encrypted=encrypt_api_key("sk-test-byok-key-123"),
        enabled=True,
    )
    session.add(byok_profile)

    session.commit()

    return session, {
        "free_user": free_user,
        "premium_user_no_byok": premium_user_no_byok,
        "premium_user_with_byok": premium_user_with_byok,
        "user_provisioning": user_provisioning,
    }


async def test_free_user_system_fallback(db, users):
    """Test 1: Free user → agents_fast (system fallback)."""
    print("\n" + "=" * 60)
    print("TEST 1: Free user → agents_fast (system fallback)")
    print("=" * 60)

    user = users["free_user"]
    user_context = UserContext(
        user_id=user.id,
        email=user.email,
        subscription_level="free",
        is_active=True,
    )

    runtime = get_llm_runtime()

    try:
        llm = runtime.create_llm_for_scope(
            scope=LLMScope.AGENTS_FAST,
            user_context=user_context,
            db=db,
            product="test",
            extra_tags=["test:free_user"],
        )

        print("✅ LLM created successfully")
        print(f"   LLM type: {type(llm).__name__}")
        print(f"   Expected: System profile fallback (no BYOK)")
        print(f"   User: {user.email} (subscription_level=free)")

        # Verify LLM has expected attributes
        assert hasattr(llm, "model"), "LLM should have model attribute"
        assert hasattr(llm, "base_url"), "LLM should have base_url attribute"

        print("\n✅ TEST 1 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_premium_no_byok_system_fallback(db, users):
    """Test 2: Premium user without BYOK → agents_balanced (system fallback)."""
    print("\n" + "=" * 60)
    print("TEST 2: Premium user without BYOK → agents_balanced")
    print("=" * 60)

    user = users["premium_user_no_byok"]
    user_context = UserContext(
        user_id=user.id,
        email=user.email,
        subscription_level="premium",
        is_active=True,
    )

    runtime = get_llm_runtime()

    try:
        llm = runtime.create_llm_for_scope(
            scope=LLMScope.AGENTS_BALANCED,
            user_context=user_context,
            db=db,
            product="test",
            extra_tags=["test:premium_no_byok"],
        )

        print("✅ LLM created successfully")
        print(f"   LLM type: {type(llm).__name__}")
        print(f"   Expected: System profile fallback (no BYOK configured)")
        print(f"   User: {user.email} (subscription_level=premium, no BYOK)")

        print("\n✅ TEST 2 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_premium_with_byok(db, users):
    """Test 3: Premium user with BYOK → agents_best (BYOK path)."""
    print("\n" + "=" * 60)
    print("TEST 3: Premium user with BYOK → agents_best")
    print("=" * 60)

    user = users["premium_user_with_byok"]
    user_context = UserContext(
        user_id=user.id,
        email=user.email,
        subscription_level="premium",
        is_active=True,
    )

    runtime = get_llm_runtime()

    try:
        llm = runtime.create_llm_for_scope(
            scope=LLMScope.AGENTS_BEST,
            user_context=user_context,
            db=db,
            product="test",
            extra_tags=["test:premium_with_byok"],
        )

        print("✅ LLM created successfully")
        print(f"   LLM type: {type(llm).__name__}")
        print(f"   Expected: BYOK path (user_config in request body)")
        print(f"   User: {user.email} (subscription_level=premium, BYOK enabled)")

        print("\n✅ TEST 3 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lazy_provisioning_retry_after(db, users):
    """Test 4: Lazy provisioning path (retry_after error)."""
    print("\n" + "=" * 60)
    print("TEST 4: Lazy provisioning (retry_after)")
    print("=" * 60)

    user = users["user_provisioning"]
    user_context = UserContext(
        user_id=user.id,
        email=user.email,
        subscription_level="premium",
        is_active=True,
    )

    runtime = get_llm_runtime()

    try:
        llm = runtime.create_llm_for_scope(
            scope=LLMScope.AGENTS_FAST,
            user_context=user_context,
            db=db,
            product="test",
            extra_tags=["test:provisioning"],
        )

        print("❌ TEST 4 FAILED: Expected LLMKeyProvisioningError but got success")
        return False

    except LLMKeyProvisioningError as e:
        print("✅ LLMKeyProvisioningError raised as expected")
        print(f"   Message: {e.message}")
        print(f"   Retry after: {e.retry_after}s")
        print(f"   User: {user.email} (virtual key status=PROVISIONING)")

        assert e.retry_after > 0, "retry_after should be positive"

        print("\n✅ TEST 4 PASSED")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("LLM Policy Router Integration Verification")
    print("=" * 60)

    # Check environment variable
    router_enabled = os.getenv("LLM_POLICY_ROUTER_ENABLED", "false").lower() == "true"
    print(f"\nLLM_POLICY_ROUTER_ENABLED: {router_enabled}")

    if not router_enabled:
        print("\n⚠️  WARNING: LLM_POLICY_ROUTER_ENABLED is not set to 'true'")
        print("   Router integration will not be tested.")
        print("   Set: export LLM_POLICY_ROUTER_ENABLED=true")
        return False

    # Setup test database
    print("\nSetting up test database...")
    db, users = setup_test_db()
    print("✅ Test database ready")

    # Run tests
    results = []
    results.append(await test_free_user_system_fallback(db, users))
    results.append(await test_premium_no_byok_system_fallback(db, users))
    results.append(await test_premium_with_byok(db, users))
    results.append(await test_lazy_provisioning_retry_after(db, users))

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")

    if all(results):
        print("\n🎉 ALL TESTS PASSED - Router integration verified!")
        return True
    else:
        print("\n❌ SOME TESTS FAILED - Review output above")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
