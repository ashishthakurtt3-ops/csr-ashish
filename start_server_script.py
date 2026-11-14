#!/usr/bin/env python
"""Start the CSR Job Intelligence Django development server."""
import sys
import os

# Add the project directory to the path
project_dir = r"D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)"
print(f"Project directory: {project_dir}", file=sys.stderr, flush=True)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
print("Setting up Django...", file=sys.stderr, flush=True)

import django
print(f"Django version: {django.VERSION}", file=sys.stderr, flush=True)

django.setup()
print("Django setup complete", file=sys.stderr, flush=True)

from django.core.management import execute_from_command_line
print("About to run manage.py runserver", file=sys.stderr, flush=True)

execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000', '--insecure'])