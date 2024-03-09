# context_processors.py
from django.contrib.auth.models import Group

from .models import NotificationTable
from .models import LeaveTable
from .models import AdminProfile
from .models import ReportTable
from .models import UserProfile

def notification_count(request):
    allowed_groups = ['admin', 'user']

    if request.user.is_authenticated and request.user.groups.filter(name__in=allowed_groups).exists():
        notifications = NotificationTable.objects.filter(receiver=request.user.username, status='delivered')
        notification_count = notifications.count()
    else:
        notification_count = 0

    return {'notification_count': notification_count}

def unread_leave_count(request):
    allowed_groups = ['admin']

    if request.user.is_authenticated and request.user.groups.filter(name='admin').exists():
        user = request.user
        admin = AdminProfile.objects.get(user=user)
        leaves = LeaveTable.objects.filter(adminID=admin, status='pending')
        leave_count = leaves.count()
    else:
        leave_count = 0

    return {'leave_count': leave_count}

def report_count(request):
    allowed_groups = ['admin']

    if request.user.is_authenticated and request.user.groups.filter(name__in=allowed_groups).exists():
        admin = AdminProfile.objects.get(user = request.user)
        reports = ReportTable.objects.filter(receiver=admin, status='delivered')
        report_count = reports.count()
    else:
        report_count = 0

    return {'report_count': report_count}
