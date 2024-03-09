from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone


from django.utils.translation import gettext_lazy as _
from ..decorators import allow_users
from ..models import IntakeTable
from ..models import UserProfile
from ..models import AdminProfile
from ..models import IntakeTable
from ..models import SubjectTable
from ..models import LeaveTable
from ..models import ReportTable
from ..models import NotificationTable
from ..models import AttendanceTable
from ..models import AttendanceStatus
from ..models import ClassTable
from system import models
from django.db.models import Count

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def userDashboard(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    intake = profile.intakeCode
    # Assuming `intakeTables` is the related name in your ClassTable model
    # Use `filter` to get ClassTable objects related to the specific intake
    class_tables = ClassTable.objects.filter(intakeTables=intake)
    class_count = class_tables.count()

    # Count the total number of related subjects across all ClassTable objects
    subject_count = class_tables.aggregate(total_subjects=Count('subjectCode', distinct=True))['total_subjects']
    absent_count = AttendanceStatus.objects.filter(userId=profile, status='absent').count()
    attendance_percentages = []

    for kelas in class_tables:
        total_classes = AttendanceTable.objects.filter(nameList=profile, classCode=kelas).count()
        attended_classes = AttendanceTable.objects.filter(attendedUser=profile, classCode=kelas).count()

        if total_classes != 0:
            attendance_percentage = attended_classes / total_classes
            formatted_percentage = "{:.0f}".format(attendance_percentage * 100)
            attendance_percentages.append({'class_name': kelas.classCode, 'percentage': formatted_percentage})

    context = {
      'intake': intake, 
      'subject_count' : subject_count,
      'class_count' : class_count,
      'absent_count' : absent_count,
      'attendance_percentages': attendance_percentages,
    }
    return render(request, 'user-templates/dashboard.html', context)


@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_subjectManagement(request):
  subjects = ClassTable.objects.all()
  if request.method == 'POST':
    searchSubject = request.POST['searchSubject']
    lists = SubjectTable.objects.filter( Q(subjectCode__icontains=searchSubject) | Q(subjectName__icontains=searchSubject)).select_related('lecturerId__user').distinct()
    return render(request, 'user-templates/subjectManagement.html', {'subjects': subjects, 'searched': searchSubject, 'lists': lists})
  return render(request, 'user-templates/subjectManagement.html', {'subjects': subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_viewSubject(request, classCode):
    kelas = ClassTable.objects.get(classCode=classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(kelas.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    context = {'kelas': kelas, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes,
               'users': selected_users, }
    return render(request, 'user-templates/viewSubject.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_absenceMonitoringManagement(request):
  return render(request, 'user-templates/dashboard.html')

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_viewAbsenceMonitoring(request):
  return render(request, 'user-templates/dashboard.html')

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_leaveManagement(request):
  leaves = LeaveTable.objects.all()
  if request.method == 'POST':
    searchLeave = request.POST['searchLeave']
    lists = leaves.filter(Q(username__icontains=searchLeave) |Q(first_name__icontains=searchLeave) |Q(last_name__icontains=searchLeave) |Q(adminprofile__adminId__icontains=searchLeave))
    return render(request, 'user-templates/leaveManagement.html', {'leaves': leaves, 'searched': searchLeave, 'lists': lists})
  else:
    return render(request, 'user-templates/leavemanagement.html', {'leaves': leaves})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_createLeave(request):
    intakes = IntakeTable.objects.all()
    if request.method == 'POST':
        adminID = request.POST['adminID']
        userID = request.POST['userID']
        leaveTitle = request.POST['leaveTitle']
        leaveDescription = request.POST['leaveDescription']
        leaveAttachment = request.FILES['leaveAttachment']
        startDate = request.POST['startDate']
        endDate = request.POST['endDate']
        applyDate = timezone.now().date()
    
        start_date_obj = timezone.datetime.strptime(startDate, '%Y-%m-%d').date()
        end_date_obj = timezone.datetime.strptime(endDate, '%Y-%m-%d').date()

        try:
            userId_instance = UserProfile.objects.get(userId=userID)
        except UserProfile.DoesNotExist:
            userId_instance = None 
        
        try:
            adminId_instance = AdminProfile.objects.get(adminId=adminID)
        except UserProfile.DoesNotExist:
            adminId_instance = None 
            

        if start_date_obj <= end_date_obj:
          leave = LeaveTable.objects.create(adminID = adminId_instance, userID = userId_instance, leaveTitle = leaveTitle, leaveDescription = leaveDescription, leaveAttachment = leaveAttachment, status = "pending", startDate = startDate, endDate = endDate, applyDate = applyDate)          
          leave.save()
        messages.success(request, _('Leave created successfully.'))
        return redirect('user-leave-management')

    return render(request, 'user-templates/createLeave.html', {'intakes': intakes, })

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_viewLeave(request, id):
    try:
        leave = LeaveTable.objects.get(id=id)
        return render(request, 'user-templates/viewLeave.html', {'leave': leave})
    except User.DoesNotExist:
        return render(request, 'error_page.html', {'error_message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_attendanceManagement(request):
  user = request.user
  profile = UserProfile.objects.get(user=user)
  attendances = AttendanceStatus.objects.filter(userId=profile).order_by('-checkIn')
  return render(request, 'user-templates/attendanceManagement.html', {'attendances': attendances})


@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_reportManagement(request):
    reports = ReportTable.objects.all()
    if request.method == 'POST':
        searchReport = request.POST['searchReport']
        lists = ReportTable.objects.filter( Q(creator__icontains=searchReport) | Q(reportTitle__icontains=searchReport))
        return render(request, 'user-templates/reportManagement.html', {'reports': reports, 'searched': searchReport, 'lists': lists})
    return render(request, 'user-templates/reportManagement.html', {'reports': reports})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_viewReport(request, id):
  report = ReportTable.objects.get(id = id)
  return render(request, 'user-templates/viewReport.html', {'report':report})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_createReport(request, id):
    user = User.objects.get(id=id)
    profile = UserProfile.objects.get(user = user)
    intakeCoder = profile.intakeCode.intakeCode
    intake = IntakeTable.objects.get(intakeCode=intakeCoder)
    admin = intake.adminId.adminId
    if request.method == "POST":
        reportTitle = request.POST['reportTitle']
        reportDescription = request.POST['reportDescription']
        receiver = request.POST['receiver']
        creator = request.POST['creator']
        try:
            adminId_instance = AdminProfile.objects.get(adminId=receiver)
        except UserProfile.DoesNotExist:
            adminId_instance = None 

        ReportTable.objects.create( reportTitle = reportTitle, reportMessage = reportDescription, creator = creator, reportDate = datetime.now(), receiver = adminId_instance,)
        return redirect('user-report-management')
    return render(request, 'user-templates/createReport.html', {'admin': admin, 'intake': intake})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_notificationManagement(request):
  notifications = NotificationTable.objects.all()
  return render(request, 'user-templates/notificationManagement.html', {'notifications':notifications})

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def user_notedNotification(request, id):
  notification = NotificationTable.objects.get(id=id)
  notification.status = "noted"
  notification.save()
  return redirect('user-notification-management')

@login_required(login_url='/')
@allow_users(allow_roles=['user'])
def viewMyProfileUser(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        normal_user = UserProfile.objects.get(user=user)
        subjects = ClassTable.objects.filter(intakeTables__intakeCode = normal_user.intakeCode.intakeCode, status = "Active" or "active")
        return render(request, 'user-templates/viewMyProfile_user.html', {'user': user, 'subjects': subjects})
    
    except User.DoesNotExist:
      return render(request, 'error_page.html', {'error_message': 'User not found'})

def user_change_language(request):
    return render(request, 'user-templates/change_language.html')





