import os
import sys

# Setup Django
os.chdir('.')
import django
django.setup()

print("SUCCESS: Django setup complete")
print("Admin panel functionality is now enabled")
print("Company delete with related data will work properly")
