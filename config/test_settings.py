"""Settings used by the test suite (see pyproject.toml)."""

import os

# Tests must run without a .env file, so give them a throwaway secret key.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-used-anywhere-else")

from config.settings import *  # noqa: F403

# Hashing passwords properly is slow on purpose. Tests do not need that.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests do not run collectstatic, so skip the manifest lookup.
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Do not scan STATIC_ROOT at startup (it does not exist in a test run).
WHITENOISE_AUTOREFRESH = True
