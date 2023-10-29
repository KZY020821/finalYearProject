import os
import django

# Set the DJANGO_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalYearProject.settings")

# Initialize Django
django.setup()

# Import Django models
from system.models import Attendance

# Use Django models
objects = Attendance.objects.all()
for obj in objects:
    print(obj.name)