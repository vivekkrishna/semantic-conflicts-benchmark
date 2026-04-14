"""Shared pytest configuration for all tests.

Loads .env from the project root so that ANTHROPIC_API_KEY and other
secrets are available to E2E tests without needing them exported in the shell.
"""

from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass
