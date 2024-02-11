from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.shortcuts import redirect, render
from django.db import transaction

from ..decorators import allow_users
from ..models import IntakeTable
from ..models import UserProfile
from ..models import LecturerProfile
from ..models import IntakeTable
from ..models import SubjectTable
from ..models import AttendanceTable

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturerDashboard(request):
  return render(request, 'lecturer-templates/dashboard.html')

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_subjectManagement(request):
  subjects = SubjectTable.objects.all()
  if request.method == 'POST':
    searchSubject = request.POST['searchSubject']
    lists = SubjectTable.objects.filter( Q(subjectCode__icontains=searchSubject) | Q(subjectName__icontains=searchSubject)).select_related('lecturerId__user').distinct()
    return render(request, 'lecturer-templates/subjectManagement.html', {'subjects': subjects, 'searched': searchSubject, 'lists': lists})
  return render(request, 'lecturer-templates/subjectManagement.html', {'subjects': subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_viewSubject(request, subjectCode):
  subject = SubjectTable.objects.get(subjectCode=subjectCode)
  intakes = IntakeTable.objects.all()
  selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
  selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
  lecturer_group = Group.objects.get(name='lecturer')
  lecturer_users = User.objects.filter(groups=lecturer_group)
  return render(request, 'lecturer-templates/viewSubject.html', {'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes':selected_intakes, 'users':selected_users, })

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_absenceMonitoringManagement(request):
  return render(request, 'lecturer-templates/dashboard.html')

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_viewAbsenceMonitoring(request):
  return render(request, 'lecturer-templates/dashboard.html')

    
@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_attendanceManagement(request):
    attendances = AttendanceTable.objects.all()
    return render(request, 'lecturer-templates/attendanceManagement.html', {'attendances':attendances})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_chooseSubject(request):
    subjects = SubjectTable.objects.all()
    if request.method == 'POST':
        subjectCode = request.POST['subjectCode']
        print(subjectCode)
        return redirect('lecturer-create-attendance', subjectCode=subjectCode)        
    return render(request, 'lecturer-templates/chooseSubject.html', {'subjects':subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_createAttendance(request, subjectCode):
    subject = SubjectTable.objects.get(subjectCode=subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)

    if request.method == "POST":
        subjectCoder = request.POST['subjectCode']
        creator = request.POST['creator']
        attendedUser = request.POST.getlist('attendedUser')
        totalUser = request.POST['totalUser']
        
        noAttendedUser = len(attendedUser)
        classDate = datetime.now()

        try:
            subject_instance = SubjectTable.objects.get(subjectCode=subjectCoder)
        except SubjectTable.DoesNotExist:
            subject_instance = None 

        attendance_instance = AttendanceTable.objects.create(
            subjectCode=subject_instance,
            creator=creator,
            totalUser=totalUser,
            noAttendedUser=noAttendedUser,
            classDate=classDate
        )

        for user_id in attendedUser:
            user_instance = UserProfile.objects.get(userId=user_id)
            attendance_instance.attendedUser.add(user_instance)

        return redirect('lecturer-attendance-management')  # Make sure this URL name is defined in your urls.py

    return render(request, 'lecturer-templates/createAttendance.html', {'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_viewAttendance(request, id):
    attendance = AttendanceTable.objects.get(id=id)
    subject = SubjectTable.objects.get(subjectCode=attendance.subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)

    # Get a list of attended user IDs
    attended_users_ids = list(attendance.attendedUser.values_list('userId', flat=True))
    print(attended_users_ids)
    return render(request, 'lecturer-templates/viewAttendance.html', {'attendance': attendance, 'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users, 'attended_users': attended_users_ids})


@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_editAttendance(request, id):
    attendance = AttendanceTable.objects.get(id=id)
    subject = SubjectTable.objects.get(subjectCode=attendance.subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)

    # Get a list of attended user IDs
    attended_users_ids = list(attendance.attendedUser.values_list('userId', flat=True))

    if request.method == "POST":
        attendedUser = request.POST.getlist('attendedUser')
        totalUser = request.POST['totalUser']

        noAttendedUser = len(attendedUser)

        # Clear existing attended users not present in the form
        for user_id in set(attended_users_ids) - set(attendedUser):
            user_instance = UserProfile.objects.get(userId=user_id)
            attendance.attendedUser.remove(user_instance)

        # Update attendance details
        attendance.totalUser = totalUser
        attendance.noAttendedUser = noAttendedUser
        attendance.save()

        # Add new attended users
        with transaction.atomic():
            for user_id in attendedUser:
                user_instance = UserProfile.objects.get(userId=user_id)
                attendance.attendedUser.add(user_instance)

        return redirect('lecturer-attendance-management')  # Make sure this URL name is defined in your urls.py

    return render(request, 'lecturer-templates/editAttendance.html', {'attendance': attendance, 'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users, 'attended_users': attended_users_ids})


def viewMyProfile_lecturer (request, user_id):
    if user_id == request.user.id:
            user = User.objects.get(id=user_id)
            lecturer_user = LecturerProfile.objects.get(user = user)
            subjects = SubjectTable.objects.filter(lecturerId = lecturer_user.lecturerId)
            return render(request, 'lecturer-templates/viewMyProfileLecturer.html', {'user': user, 'subjects': subjects, })
    else:
        message = 'Sorry, you are not allowed to view this page'
        return render(request, 'error.html', {'message': message})