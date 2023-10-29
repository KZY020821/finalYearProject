from .models import Profile, Attendance as attendanceModel, subject
# , subject, intake, location
from django.contrib import admin

# Register your models here.
admin.site.register(Profile)
admin.site.register(attendanceModel)
admin.site.register(subject)