#!/usr/bin/env python3
"""
Script to verify test database setup and create test database if needed.

This script helps ensure tests don't accidentally run against production database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Check test database configuration."""
    print("=" * 70)
    print("Test Database Setup Verification")
    print("=" * 70)
    print()

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    prod_db = os.getenv("DATABASE_URL")
    test_db = os.getenv("TEST_DATABASE_URL")

    print("📊 Current Configuration:")
    print(f"   Production DB: {prod_db}")
    print(f"   Test DB:       {test_db}")
    print()

    # Validation checks
    errors = []
    warnings = []

    if not test_db:
        errors.append("❌ TEST_DATABASE_URL is not set in .env")
        errors.append(
            "   Add: TEST_DATABASE_URL=postgresql://user:pass@host/dbname_test?ssl=require"
        )

    if test_db == prod_db:
        errors.append("❌ CRITICAL: Test database is same as production database!")
        errors.append("   This will DELETE all production data during tests.")
        errors.append("   Create a separate database for testing.")

    if test_db and "test" not in test_db.lower():
        warnings.append("⚠️  WARNING: Test database URL doesn't contain 'test'")
        warnings.append("   Consider using a database name like 'neondb_test'")

    # Display results
    if errors:
        print("🚨 ERRORS FOUND:")
        for error in errors:
            print(f"   {error}")
        print()
        print("Fix these errors before running tests!")
        return 1

    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print()

    if not errors:
        print("✅ Test database configuration looks good!")
        print()
        print("Next Steps:")
        print("   1. Create the test database in your provider (if not exists)")
        print("      - For Neon: Create new database branch or database")
        print("      - Name it: neondb_test (or similar)")
        print()
        print("   2. Run tests:")
        print("      pytest")
        print()
        print("   3. Tests will automatically:")
        print("      - Create tables in test database")
        print("      - Run tests")
        print("      - Clean up after each test")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
