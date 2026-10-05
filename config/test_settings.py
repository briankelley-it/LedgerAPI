"""Settings used by the test suite (see pyproject.toml)."""

import os

# Tests must run without a .env file, so give them a throwaway secret key.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-used-anywhere-else")

from config.settings import *  # noqa: F403

# Hashing passwords properly is slow on purpose. Tests do not need that.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
