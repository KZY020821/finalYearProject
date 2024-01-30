from .models import Profile, Attendance as attendanceModel, subject, intake, leave, feedback, UserProfile, AdminProfile, AbsenceMonitoringTable, AttendanceTable, LeaveTable, LecturerProfile, SubjectTable, IntakeTable, ReportTable, NotificationTable
from django.contrib import admin

# Register your models here.
admin.site.register(Profile)
admin.site.register(attendanceModel)
admin.site.register(subject)
admin.site.register(intake)
admin.site.register(leave)
admin.site.register(feedback)
admin.site.register(UserProfile)
admin.site.register(AdminProfile)
admin.site.register(AbsenceMonitoringTable)
admin.site.register(AttendanceTable)
admin.site.register(LeaveTable)
admin.site.register(LecturerProfile)
admin.site.register(SubjectTable)
admin.site.register(IntakeTable)
admin.site.register(ReportTable)
admin.site.register(NotificationTable)