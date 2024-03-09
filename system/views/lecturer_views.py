import os
import subprocess
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render

from ..decorators import allow_users
from ..models import AttendanceStatus
from ..models import AttendanceTable
from ..models import ClassTable
from ..models import IntakeTable
from ..models import LecturerProfile
from ..models import SubjectTable
from ..models import UserProfile
from django.utils.translation import gettext_lazy as _


@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturerDashboard(request):
    user = request.user
    lecturer = LecturerProfile.objects.get(user = user)
    classes_count = ClassTable.objects.filter( lecturerId = lecturer).count()
    classes = ClassTable.objects.filter(lecturerId = lecturer)
    classes = ClassTable.objects.filter(lecturerId=lecturer)
    attendances = []

    class_data = []

    for kelas in classes:
        attendance = AttendanceTable.objects.filter(classCode=kelas)
        class_total_attendances = 0
        class_total_percentage = 0

        for att in attendance:
            if att.totalUser != 0:
                attendance_percentage = att.noAttendedUser / att.totalUser * 100
                formatted_percentage = int(round(attendance_percentage))

                class_total_attendances += 1
                class_total_percentage += formatted_percentage

                attendances.append({'class_name': kelas.classCode, 'percentage': formatted_percentage})

        if class_total_attendances != 0:
            average_percentage = class_total_percentage / class_total_attendances
            class_data.append({'class_name': kelas.classCode, 'average_percentage': round(average_percentage)})

    context = {
        'classes_count': classes_count,
        'classes': classes,
        'class_data': class_data,
    }
    return render(request, 'lecturer-templates/dashboard.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_subjectManagement(request):
    user = request.user
    lecturer = LecturerProfile.objects.get(user = user)
    subjects = ClassTable.objects.filter( lecturerId = lecturer)
  
    return render(request, 'lecturer-templates/subjectManagement.html', {'subjects': subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_viewSubject(request, subjectCode):
  subject = ClassTable.objects.get(classCode=subjectCode)
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
    user = request.user
    lecturer = LecturerProfile.objects.get(user = user)
    classes = ClassTable.objects.filter(lecturerId = lecturer)
    attendances = []
    for kelas in classes:
        attendance = AttendanceTable.objects.filter(classCode = kelas).order_by('-classDate')
        attendances.extend(attendance)
    context = {
        'attendances' : attendances,

    }
    return render(request, 'lecturer-templates/attendanceManagement.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_chooseSubject(request):
    user = request.user
    lecturer = LecturerProfile.objects.get(user = user)
    subjects = ClassTable.objects.filter(lecturerId = lecturer)
    if request.method == 'POST':
        subjectCoder = request.POST['subjectCode']
        return redirect('lecturer-create-attendance', classCode=subjectCoder)
    return render(request, 'lecturer-templates/chooseSubject.html', {'subjects':subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_createAttendance(request, classCode):
    kelas = ClassTable.objects.get(classCode = classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = kelas.intakeTables.all()
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    subject = SubjectTable.objects.get(subjectCode = kelas.subjectCode.subjectCode)

    context = {
        'kelas': kelas,
        'lecturers': lecturer_users,
        'intakes': intakes,
        'selected_intakes': selected_intakes,
        'users': selected_users,
        'subject': subject}

    if request.method == "POST":
        classCoder = request.POST['classCode']
        creator = request.POST['creator']
        attendedUser = request.POST.getlist('attendedUser')
        totalUser = request.POST['totalUser']
        method = "manual"
        noAttendedUser = len(attendedUser)
        classDate = datetime.now()

        try:
            class_instance = ClassTable.objects.get(classCode=classCoder)
        except ClassTable.DoesNotExist:
            class_instance = None

        attendance_instance = AttendanceTable.objects.create(
            classCode=class_instance,
            creator=creator,
            totalUser=totalUser,
            noAttendedUser=noAttendedUser,
            classDate=classDate,
            method="Manual"
        )

        relation_instance = AttendanceTable.objects.get(id=attendance_instance.id)
        for id in attendedUser:
            relation_instance.attendedUser.add(id)

        for user_id in selected_users:
            relation_instance.nameList.add(user_id)

        for user in selected_users:
            AttendanceStatus.objects.create(
                relation_id=relation_instance,
                userId=user,
            )

        for user_id in attendedUser:
            user = UserProfile.objects.get(userId=user_id)
            specific_attendance = AttendanceStatus.objects.get(
                relation_id=relation_instance,
                userId=user,
            )
            specific_attendance.status = 'attended'
            specific_attendance.save()

        return redirect('lecturer-attendance-management')  # Make sure this URL name is defined in your urls.py

    return render(request, 'lecturer-templates/createAttendance.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_viewAttendance(request, id):
    attendance = AttendanceTable.objects.get(id=id)
    kelas = ClassTable.objects.get(classCode = attendance.classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(kelas.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    attendance_status = AttendanceStatus.objects.filter(relation_id = attendance.id)
    context = {
        'attendance': attendance,
        'kelas': kelas,
        'intakes': intakes,
        'selected_intakes': selected_intakes,
        'users': selected_users,
        'attendance_status' : attendance_status
        }
    return render(request, 'lecturer-templates/viewAttendance.html', context)


@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_editAttendance(request, id):
    attendance = AttendanceTable.objects.get(id=id)
    kelas = ClassTable.objects.get(classCode=attendance.classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(kelas.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    attendance_status = AttendanceStatus.objects.filter(relation_id=attendance.id)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    intakeTables = kelas.intakeTables.all()
    subjects = SubjectTable.objects.all()
    context = {
        'attendance': attendance,
        'kelas': kelas,
        'intakes': intakes,
        'selected_intakes': selected_intakes,
        'users': selected_users,
        'attendance_status': attendance_status,
        'intakeTables': intakeTables,
        'lecturers': lecturer_users,
        'subjects': subjects,
    }

    name_list = []
    if request.method == "POST":
        student_statuses = {}

        noOfAttendedUser = 0
        attendedUser = []
        for status in attendance_status:
            student_id = status.userId.userId
            status_value = request.POST.get(f"status_{student_id}")
            status.status = status_value.lower()
            if status_value.lower() == 'attended':
                noOfAttendedUser += 1
                attendedUser.append(student_id)
            status.save()

        attendance.attendedUser.set('')
        attendance.save()

        for user in attendedUser:
            user_instance = UserProfile.objects.get(userId=user)
            attendance.attendedUser.add(user_instance)

        attendance.noAttendedUser = noOfAttendedUser
        attendance.save()

        return redirect('lecturer-attendance-management')  # Make sure this URL name is defined in your urls.py

    return render(request, 'lecturer-templates/editAttendance.html', context)


def viewMyProfile_lecturer (request, user_id):
    if user_id == request.user.id:
            user = User.objects.get(id=user_id)
            lecturer_user = LecturerProfile.objects.get(user = user)
            subjects = ClassTable.objects.filter(lecturerId = lecturer_user.lecturerId)
            return render(request, 'lecturer-templates/viewMyProfileLecturer.html', {'user': user, 'subjects': subjects, })
    else:
        message = _('Sorry, you are not allowed to view this page')
        return render(request, 'error.html', {'message': message})


@login_required(login_url='/')
@allow_users(allow_roles=['lecturer'])
def lecturer_face(request, user_id):
    if user_id == request.user.id:
        if request.method == "POST":
            classCode = request.POST['classCode']
            virtualenv_path = "myenv"
            python_path = os.path.join(virtualenv_path, "bin", "python")
            main_script_path = f"/Users/khorzeyi/code/finalYearProject/face_rec-master/face_rec_lec.py"
            creator = request.user.username
            command = [python_path, main_script_path, classCode, creator]
            try:
                subprocess.run(command, capture_output=True, text=True, shell=False)
            except subprocess.CalledProcessError as e:
                pass

            user_instance = User.objects.get(id=request.user.id)
            if user_instance.groups.exists():
                if user_instance.groups.first().name == 'admin':
                    return redirect('admin-dashboard')
                elif user_instance.groups.first().name == 'lecturer':
                    return redirect('lecturer-dashboard')
                else:
                    return redirect('user-dashboard')
        user = request.user
        lecturer = LecturerProfile.objects.get(user = user)
        kelas = ClassTable.objects.filter(lecturerId = lecturer)
        return render(request, 'lecturer-templates/lecturer_face.html', {'kelas': kelas})
    else:
        message = _('Sorry, you are not allowed to view this page')
        return render(request, 'error.html', {'message': message})


def collect_attendance(ids, classCode, creator):
    try:
        class_instance = ClassTable.objects.get(classCode=classCode)
    except ClassTable.DoesNotExist:
        return HttpResponse("Class not found", status=404)

    selected_intakes = list(class_instance.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)

    classDate = datetime.now()
    noAttendedUser = len(ids)

    if 'unknown' in ids:
        noAttendedUser -= 1

    totalUser = class_instance.noOfUser

    attendance_instance = AttendanceTable.objects.create(
        classCode=class_instance,
        creator=creator,
        totalUser=totalUser,
        noAttendedUser=noAttendedUser,
        classDate=classDate,
        method="face recognition"
    )

    relation_instance = AttendanceTable.objects.get(id=attendance_instance.id)
    users_dict = UserProfile.objects.in_bulk(ids)

    for user_id in ids:
        user = users_dict.get(user_id)
        if user:
            relation_instance.attendedUser.add(user)

    for user in selected_users:
        relation_instance.nameList.add(user)

    for user_id in selected_users:
        AttendanceStatus.objects.create(
            relation_id=relation_instance,
            userId=user_id,
        )

    for user_id in ids:
        user = users_dict.get(user_id.split('_')[0])
        if user:
            specific_attendance = AttendanceStatus.objects.get(
                relation_id=relation_instance,
                userId=user,
            )
            specific_attendance.status = 'attended'
            specific_attendance.save()

def lecturer_change_language(request):
    return render(request, 'lecturer-templates/change_language.html')