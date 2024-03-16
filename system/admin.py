from .models import UserProfile
from .models import AdminProfile
from .models import AbsenceMonitoringTable
from .models import AttendanceTable
from .models import LeaveTable
from .models import LecturerProfile
from .models import SubjectTable
from .models import IntakeTable
from .models import ReportTable
from .models import NotificationTable
from .models import ClassTable
from .models import AttendanceStatus

from import_export.admin import ImportExportActionModelAdmin

from django.contrib import admin
# Register your models here.
admin.site.register(UserProfile, ImportExportActionModelAdmin)
admin.site.register(AdminProfile)
admin.site.register(AbsenceMonitoringTable)
admin.site.register(AttendanceTable)
admin.site.register(LeaveTable)
admin.site.register(LecturerProfile)
admin.site.register(SubjectTable)
admin.site.register(IntakeTable)
admin.site.register(ReportTable)
admin.site.register(NotificationTable)
admin.site.register(ClassTable)
admin.site.register(AttendanceStatus)