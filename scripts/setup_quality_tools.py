#!/usr/bin/env python3
"""Setup script for code quality tools and pre-commit hooks."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"⚙️  {description}")
    print(f"{'=' * 60}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e}")
        return False


def main() -> int:
    """Run setup for code quality tools."""
    print("\n🚀 Setting up code quality tools for Medico24 Backend\n")

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Are you in the project root?")
        return 1

    success = True

    # Install dependencies
    success &= run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"], "Installing dependencies"
    )

    # Install pre-commit hooks
    success &= run_command(["pre-commit", "install"], "Installing pre-commit hooks")

    success &= run_command(
        ["pre-commit", "install", "--hook-type", "commit-msg"], "Installing commit-msg hooks"
    )

    # Create baseline for detect-secrets if it doesn't exist
    if not Path(".secrets.baseline").exists():
        success &= run_command(
            ["detect-secrets", "scan", "--baseline", ".secrets.baseline"],
            "Creating detect-secrets baseline",
        )

    # Run pre-commit on all files (optional, can be slow)
    print("\n" + "=" * 60)
    response = input("⚠️  Run pre-commit on all files? This may take a while. (y/N): ")
    if response.lower() in ["y", "yes"]:
        success &= run_command(
            ["pre-commit", "run", "--all-files"], "Running pre-commit on all files"
        )

    print("\n" + "=" * 60)
    if success:
        print("✅ Setup completed successfully!")
        print("\n📚 Next steps:")
        print("  1. Read LINTING.md for detailed documentation")
        print("  2. Pre-commit hooks will run automatically on git commit")
        print("  3. Use 'make lint' or 'make format' to check code manually")
        print("  4. Use 'make precommit' to run all hooks manually")
        print("\n💡 Tips:")
        print("  - VS Code will format on save if extensions are installed")
        print("  - Run 'pre-commit run --all-files' to check all files")
        print("  - Use 'git commit --no-verify' to skip hooks (emergency only)")
    else:
        print("❌ Setup completed with errors. Please check the output above.")
        return 1

    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
