"""Convenience entry point for seeding the Django database.

Examples:
    python seed.py
    python seed.py --fresh
    python seed.py --admin-password "YourNewPassword"
"""

from __future__ import annotations

import os
import sys


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.management import execute_from_command_line  # noqa: E402


if __name__ == "__main__":
    execute_from_command_line([sys.argv[0], "seed_database", *sys.argv[1:]])
