import math
import os
import shutil
import subprocess
import sys
from datetime import datetime

import cv2
import face_recognition
import numpy as np
from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import authenticate, get_user, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core.files.storage import FileSystemStorage, default_storage
from django.db.models import Q
from django.http import (Http404, HttpResponse, JsonResponse,
                         StreamingHttpResponse)
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import allow_users, unauthenticated_user
from ..models import AbsenceMonitoringTable
from ..models import Attendance as attendanceModel
from ..models import IntakeTable
from ..models import Profile as personalinfo
from ..models import UserProfile
from ..models import feedback as feedbackTable
from ..models import intake as intakeTable
from ..models import leave
from ..models import AdminProfile
from ..models import LecturerProfile
from ..models import IntakeTable
from ..models import SubjectTable
from ..models import LeaveTable
from ..models import AttendanceTable
from ..models import ReportTable
from ..models import NotificationTable

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def adminDashboard(request):
    count_userAbsence()

    attendances = AttendanceTable.objects.all()
    user = User.objects.get(id=request.user.id)
    admin = AdminProfile.objects.get(user=user)
    intakes = IntakeTable.objects.filter(adminId=admin.adminId)

    intake_data = {}  

    for attendance in attendances:
        for intake in intakes:
            if intake in attendance.subjectCode.intakeTables.all():
                intake_total = UserProfile.objects.filter(intakeCode=intake.intakeCode)
                intake_attended = attendance.attendedUser.filter(intakeCode=intake.intakeCode)

                if intake.intakeCode not in intake_data:
                    intake_data[intake.intakeCode] = {
                        'attended_sum': intake_attended.count(),
                        'total_sum': intake_total.count(),
                        'count': 1  
                    }
                else:
                    intake_data[intake.intakeCode]['attended_sum'] += intake_attended.count()
                    intake_data[intake.intakeCode]['total_sum'] += intake_total.count()
                    intake_data[intake.intakeCode]['count'] += 1

    average_percentages = {}
    for intake_code, data in intake_data.items():
        attended_sum = data['attended_sum']
        total_sum = data['total_sum']
        count = data['count']

        average_percentage = (attended_sum / total_sum)*100 if total_sum != 0 else 0
        average_percentage = format(average_percentage, ".0f")
        average_percentages[intake_code] = {
            'average_percentage': average_percentage,
            'occurrences': count
        }

    return render(request, 'admin-templates/dashboard.html', {'average_percentages': average_percentages})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_adminManagement(request):
    admin_group = Group.objects.get(name='admin')
    admin_users = User.objects.filter(groups=admin_group)
    if request.method == 'POST':
        searchAdmin = request.POST['searchAdmin']
        lists = AdminProfile.objects.filter(Q(user__username__icontains=searchAdmin) | Q(user__first_name__icontains=searchAdmin) | Q(user__last_name__icontains=searchAdmin) | Q(adminId__icontains=searchAdmin))
        return render(request, 'admin-templates/adminManagement.html', {'users': admin_users, 'searched': searchAdmin, 'lists': lists})
    else:
        return render(request, 'admin-templates/adminManagement.html', {'users': admin_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createAdmin(request):
    if request.method == 'POST':
        adminID = request.POST['adminID']
        adminEmail = request.POST['adminEmail']
        firstName = request.POST['first_name']
        lastName = request.POST['last_name']
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        profileImage = request.FILES.get('image')

        if User.objects.filter(email=adminEmail).exists():
            messages.error(request, 'Email used')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username used')
        elif AdminProfile.objects.filter(adminId=adminID).exists():
            messages.error(request, 'Admin ID used')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match')
        else:
            user = User.objects.create_user(username=username, email=adminEmail, password=password1, first_name=firstName, last_name=lastName)
            user.save()

            group = Group.objects.get(name='admin')
            user.groups.add(group)

            admin_profile = AdminProfile(user=user, adminId=adminID, adminProfileImage=profileImage)
            admin_profile.save()

            messages.success(request, 'Admin created successfully.')
            return redirect('admin-admin-management')

    return render(request, 'admin-templates/createAdmin.html')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editAdmin(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        if request.method == 'POST':
          adminID = request.POST['adminID']
          adminEmail = request.POST['adminEmail']
          firstName = request.POST['first_name']
          lastName = request.POST['last_name']
          username = request.POST['username']
          profileImage = request.FILES.get('image')

          if User.objects.filter(email=adminEmail).exclude(id=user_id).exists():
              messages.error(request, 'Email used')
          elif User.objects.filter(username=username).exclude(id=user_id).exists():
              messages.error(request, 'Username used')
          elif AdminProfile.objects.filter(adminId=adminID).exclude(user=user).exists():
              messages.error(request, 'Admin ID used')
          else:
            user.email = adminEmail
            user.first_name = firstName
            user.last_name = lastName
            user.username = username
            user.save()
            
            admin_profile = user.adminprofile
            admin_profile.adminId = adminID
            
            
            if profileImage:
              admin_profile_image_path = admin_profile.adminProfileImage.path

              if os.path.exists(admin_profile_image_path):
                  os.remove(admin_profile_image_path)

              admin_profile.adminProfileImage = profileImage

            admin_profile.save()
            
            messages.success(request, 'Modification have been saved successfully.')
            return redirect('admin-admin-management')
        return render(request, 'admin-templates/editAdmin.html', {'user': user})
    except User.DoesNotExist:
        return render(request, 'error.html', {'message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewAdmin(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        return render(request, 'admin-templates/viewAdmin.html', {'user': user})
    except User.DoesNotExist:
        return render(request, 'error.html', {'message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeAdmin(request):
  if request.method == 'POST':
    user_id = request.POST.get('user_id')
    try:
        user = User.objects.get(id=user_id)
        admin_profile_image_path = user.adminprofile.adminProfileImage.path
        
        # Delete user and related profile
        user.delete()
        
        # Remove the admin's profile image file
        if os.path.exists(admin_profile_image_path):
            os.remove(admin_profile_image_path)

        messages.success(request, 'Admin removed successfully.')
        return redirect('admin-admin-management')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
  return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_lecturerManagement(request):
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    if request.method == 'POST':
        searchLecturer = request.POST['searchLecturer']
        lists = LecturerProfile.objects.filter(Q(user__username__icontains=searchLecturer) | Q(user__first_name__icontains=searchLecturer) | Q(user__last_name__icontains=searchLecturer) | Q(lecturerId__icontains=searchLecturer))
        return render(request, 'admin-templates/LecturerManagement.html', {'users': lecturer_users, 'searched': searchLecturer, 'lists': lists})
    return render(request, 'admin-templates/lecturerManagement.html', {'users': lecturer_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createLecturer(request):
  if request.method == 'POST':
    lecturerID = request.POST['lecturerID']
    lecturerEmail = request.POST['lecturerEmail']
    firstName = request.POST['first_name']
    lastName = request.POST['last_name']
    username = request.POST['username']
    password1 = request.POST['password1']
    password2 = request.POST['password2']
    profileImage = request.FILES.get('image')

    if User.objects.filter(email=lecturerEmail).exists():
        messages.error(request, 'Email used')
    elif User.objects.filter(username=username).exists():
        messages.error(request, 'Username used')
    elif LecturerProfile.objects.filter(lecturerId=lecturerID).exists():
        messages.error(request, 'Lecturer ID used')
    elif password1 != password2:
        messages.error(request, 'Passwords do not match')
    else:
        user = User.objects.create_user(username=username, email=lecturerEmail, password=password1, first_name=firstName, last_name=lastName)
        user.save()

        group = Group.objects.get(name='lecturer')
        user.groups.add(group)

        lecturer_profile = LecturerProfile(user=user, lecturerId=lecturerID, lecturerProfileImage=profileImage)
        lecturer_profile.save()
        messages.success(request, 'Lecturer created successfully.')
        return redirect('admin-lecturer-management')
  return render(request, 'admin-templates/createLecturer.html')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editLecturer(request, user_id):
  try:
      user = User.objects.get(id=user_id)
      if request.method == 'POST':
        lecturerID = request.POST['lecturerID']
        lecturerEmail = request.POST['lecturerEmail']
        firstName = request.POST['first_name']
        lastName = request.POST['last_name']
        username = request.POST['username']
        profileImage = request.FILES.get('image')

        if User.objects.filter(email=lecturerEmail).exclude(id=user_id).exists():
            messages.error(request, 'Email used')
        elif User.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, 'Username used')
        elif LecturerProfile.objects.filter(lecturerId=lecturerID).exclude(user=user).exists():
            messages.error(request, 'lecturer ID used')
        else:
          user.email = lecturerEmail
          user.first_name = firstName
          user.last_name = lastName
          user.username = username
          user.save()
          
          lecturer_profile = user.lecturerprofile
          lecturer_profile.lecturerId = lecturerID
          
          
          if profileImage:
            lecturer_profile_image_path = lecturer_profile.lecturerProfileImage.path

            if os.path.exists(lecturer_profile_image_path):
                os.remove(lecturer_profile_image_path)

            lecturer_profile.lecturerProfileImage = profileImage

          lecturer_profile.save()
          
          messages.success(request, 'Modification have been saved successfully.')
          return redirect('admin-lecturer-management')
      return render(request, 'admin-templates/editLecturer.html', {'user': user})
  except User.DoesNotExist:
      return render(request, 'error.html', {'message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewLecturer(request, user_id):
  try:
      user = User.objects.get(id=user_id)
      return render(request, 'admin-templates/viewLecturer.html', {'user': user})
  except User.DoesNotExist:
      return render(request, 'error.html', {'message': 'User not found'})


@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeLecturer(request):
  if request.method == 'POST':
    user_id = request.POST.get('user_id')
    try:
        user = User.objects.get(id=user_id)
        lecturer_profile_image_path = user.lecturerprofile.lecturerProfileImage.path
        
        # Delete user and related profile
        user.delete()
        
        # Remove the admin's profile image file
        if os.path.exists(lecturer_profile_image_path):
            os.remove(lecturer_profile_image_path)

        messages.success(request, 'Lecturer removed successfully.')
        return redirect('admin-lecturer-management')
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
  return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_userManagement(request):
    user_group = Group.objects.get(name='user')
    normal_users = User.objects.filter(groups=user_group)
    if request.method == 'POST':
        searchUser = request.POST['searchUser']
        lists = UserProfile.objects.filter(Q(user__username__icontains=searchUser) | Q(user__first_name__icontains=searchUser) | Q(user__last_name__icontains=searchUser) | Q(userId__icontains=searchUser))
        return render(request, 'admin-templates/userManagement.html', {'users': normal_users, 'searched': searchUser, 'lists': lists})
    return render(request, 'admin-templates/userManagement.html', {'users': normal_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createUser(request):
  if request.method == "POST":
        id = request.POST['studentID']
        email = request.POST['studentEmail']
        password = request.POST['password1']
        password2 = request.POST['password2']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        intakeCode = request.POST['intakeCode']
        faceimage = request.FILES.get('image')  # Use request.FILES for file input

        if password != password2:
            messages.error(request, "Password not same")
            return redirect('admin-create-user') 
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect('admin-create-user') 
        elif User.objects.filter(username=id).exists():
            messages.error(request, "studentID already used")
            return redirect('admin-create-user') 
        else:
            try:
                intake_instance = IntakeTable.objects.get(intakeCode=intakeCode)
            except IntakeTable.DoesNotExist:
                intake_instance = None 
            
            try:
                absenceMonitoring_instance = AbsenceMonitoringTable.objects.get(id=1)
            except AbsenceMonitoringTable.DoesNotExist:
                absenceMonitoring_instance = None 
            
            if intake_instance:
                user = User.objects.create_user(username=username , email=email, password=password, first_name=first_name, last_name=last_name)
                user.save()

                user_profile = UserProfile(user=user, userId=id, intakeCode=intake_instance, absenceMonitoringId=absenceMonitoring_instance, faceImageUrl=faceimage)
                user_profile.save()

                group = Group.objects.get(name='user')
                user.groups.add(group)

                messages.success(request, "User created successfully.")
                return redirect("admin-user-management")
            else: 
                messages.error(request, "register failed.")
                return redirect("register")
       
  intakes = IntakeTable.objects.all()
  return render(request, 'admin-templates/createUser.html', {'intakes': intakes, })

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editUser(request, user_id):
    intakes = IntakeTable.objects.all()
    try:
        user = User.objects.get(id=user_id)
        if request.method == 'POST':
            userID = request.POST['userID']
            userEmail = request.POST['userEmail']
            firstName = request.POST['first_name']
            lastName = request.POST['last_name']
            username = request.POST['username']
            profileImage = request.FILES.get('image')
            intakeCode = request.POST['intakeCode']
            if User.objects.filter(email=userEmail).exclude(id=user_id).exists():
                messages.error(request, 'Email used')
            elif User.objects.filter(username=username).exclude(id=user_id).exists():
                messages.error(request, 'Username used')
            elif UserProfile.objects.filter(userId=userID).exclude(user=user).exists():
                messages.error(request, 'user ID used')
            else:
                try:
                    intake_instance = IntakeTable.objects.get(intakeCode=intakeCode)
                except IntakeTable.DoesNotExist:
                    intake_instance = None 

                user.email = userEmail
                user.first_name = firstName
                user.last_name = lastName
                user.username = username
                user.save()
                
                profile = user.userprofile
                profile.intakeCode = intake_instance
                profile.save()

                user_profile = user.userprofile
                user_profile.userId = userID

                if profileImage:
                    user_profile_image_path = user_profile.faceImageUrl.path

                    if os.path.exists(user_profile_image_path):
                        os.remove(user_profile_image_path)


                    user_profile.faceImageUrl = profileImage

                    user_profile.save()

                messages.success(request, 'Modification have been saved successfully.')
                return redirect('admin-user-management')
        return render(request, 'admin-templates/editUser.html', {'user': user, 'intakes': intakes})
    except User.DoesNotExist:
        return render(request, 'error.html', {'message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewUser(request, user_id):
  try:
      user = User.objects.get(id=user_id)
      return render(request, 'admin-templates/viewUser.html', {'user': user})
  except User.DoesNotExist:
      return render(request, 'error.html', {'message': 'User not found'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeUser(request):
  if request.method == 'POST':
      user_id = request.POST.get('user_id')
      try:
          user = User.objects.get(id=user_id)
          user_profile_image_path = user.userprofile.faceImageUrl.path
          
          # Delete user and related profile
          user.delete()
          
          # Remove the admin's profile image file
          if os.path.exists(user_profile_image_path):
              os.remove(user_profile_image_path)

          messages.success(request, 'User removed successfully.')
          return redirect('admin-user-management')
      except User.DoesNotExist:
          return JsonResponse({'success': False, 'message': 'User not found'})
  return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_intakeManagement(request):
    intakes = IntakeTable.objects.all()
    return render(request, 'admin-templates/intakeManagement.html', {'intakes': intakes})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createIntake(request):
    admin_group = Group.objects.get(name='admin')
    admin_users = User.objects.filter(groups=admin_group)

    if request.method == 'POST':
        intakeCode = request.POST['intakeCode']
        adminId = request.POST['adminId']

        if IntakeTable.objects.filter(intakeCode=intakeCode).exists():
            messages.error(request, 'Intake code is already in use')
            return redirect('admin-create-intake')

        try:
            admin_profile_instance = AdminProfile.objects.get(adminId=adminId)
        except AdminProfile.DoesNotExist:
            admin_profile_instance = None 

        IntakeTable.objects.create(intakeCode=intakeCode, adminId=admin_profile_instance)

        messages.success(request, 'Intake created successfully')
        return redirect('admin-intake-management')

    return render(request, 'admin-templates/createIntake.html', {'admins': admin_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editIntake(request, intakeCode):
    intake = IntakeTable.objects.get(intakeCode=intakeCode)
    admin_group = Group.objects.get(name='admin')
    admin_users = User.objects.filter(groups=admin_group)
    if request.method == 'POST':
        intakecoder = request.POST['intakeCode']
        adminId = request.POST['adminId']

        if IntakeTable.objects.filter(intakeCode=intakecoder).exclude(pk=intake.pk).exists():
            messages.error(request, 'Intake code is already in use')
            return redirect('admin-intake-management')
        try:
            admin_profile_instance = AdminProfile.objects.get(adminId=adminId)
        except AdminProfile.DoesNotExist:
            admin_profile_instance = None 

        intake.intakeCode = intakecoder
        intake.adminId = admin_profile_instance
        intake.save()

        messages.success(request, 'Intake updated successfully')
        return redirect('admin-intake-management')
    
    return render(request, 'admin-templates/editIntake.html', {'intake': intake, 'admins': admin_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewIntake(request, intakeCode):
    intake = get_object_or_404(IntakeTable, intakeCode=intakeCode)
    intake_users = UserProfile.objects.filter(intakeCode=intakeCode)
    users = User.objects.filter(userprofile__in=intake_users)
    return render(request, 'admin-templates/viewIntake.html', {'intake': intake, 'users': users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeIntake(request):
    if request.method == 'POST':
        intakeCode = request.POST.get('intakeCode')
        intake = get_object_or_404(IntakeTable, intakeCode=intakeCode)
        
        intake.delete()
        
        messages.success(request, 'Intake removed successfully.')
        return redirect('admin-intake-management')

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_subjectManagement(request):
    subjects = SubjectTable.objects.all()
    return render(request, 'admin-templates/subjectManagement.html', {'subjects': subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createSubject(request):
    intakes = IntakeTable.objects.all()
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)

    if request.method == 'POST':
        subjectCode = request.POST['subjectCode']
        subjectName = request.POST['subjectName']
        lecturerId = request.POST['lecturerId']
        selected_intakes = request.POST.getlist('intakes')
        if SubjectTable.objects.filter(subjectCode=subjectCode).exists():
            messages.error(request, 'Subject code is already in use')
            return redirect('admin-create-subject')
        try:
            lecturer_instance = LecturerProfile.objects.get(lecturerId=lecturerId)
        except LecturerProfile.DoesNotExist:
            lecturer_instance = None 

        subject = SubjectTable.objects.create(subjectCode=subjectCode, subjectName=subjectName, lecturerId=lecturer_instance, status = 'Active')
        subject.intakeTables.set(IntakeTable.objects.filter(intakeCode__in=selected_intakes))
        
        folder_path = os.path.join('media', subjectCode)
        os.makedirs(folder_path, exist_ok=True)
        
        for intake_code in selected_intakes:
            users_to_copy = UserProfile.objects.filter(intakeCode=intake_code)
            for user in users_to_copy:
                source_path = os.path.join('media', user.faceImageUrl.name)
                destination_path = os.path.join(folder_path, os.path.basename(user.faceImageUrl.name))
                shutil.copy2(source_path, destination_path)

        subject.noOfUser = UserProfile.objects.filter(intakeCode__in=subject.intakeTables.all()).count()
        subject.save()
        messages.success(request, 'Subject created successfully')
        return redirect('admin-subject-management')

    return render(request, 'admin-templates/createSubject.html', {'intakes': intakes, 'lecturers': lecturer_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editSubject(request, subjectCode):
    subject = SubjectTable.objects.get(subjectCode=subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    if request.method == 'POST':
        subjectCoder = request.POST['subjectCode']
        subjectName = request.POST['subjectName']
        lecturerId = request.POST['lecturerId']
        selected_intakes = request.POST.getlist('intakes')
        
        if SubjectTable.objects.filter(subjectCode=subjectCoder).exclude(subjectCode=subjectCoder).exists():
            messages.error(request, 'Subject code is already in use')
            return redirect('admin-edit-subject')
        try:
            lecturer_instance = LecturerProfile.objects.get(lecturerId=lecturerId)
        except LecturerProfile.DoesNotExist:
            lecturer_instance = None 

        subject.subjectCode = subjectCoder
        subject.subjectName = subjectName
        subject.lecturerId = lecturer_instance
        subject.intakeTables.set(IntakeTable.objects.filter(intakeCode__in=selected_intakes))
        subject.noOfUser = UserProfile.objects.filter(intakeCode__in=subject.intakeTables.all()).count()
        subject.save()

        folder_path = os.path.join('media', subjectCoder)

        # Remove the existing folder and its content
        shutil.rmtree(folder_path, ignore_errors=True)

        # Recreate the folder
        os.makedirs(folder_path, exist_ok=True)

        for intake_code in selected_intakes:
            users_to_copy = UserProfile.objects.filter(intakeCode=intake_code)
            for user in users_to_copy:
                source_path = os.path.join('media', user.faceImageUrl.name)
                destination_path = os.path.join(folder_path, os.path.basename(user.faceImageUrl.name))
                shutil.copy2(source_path, destination_path)

        messages.success(request, 'Subject updated successfully')
        return redirect('admin-subject-management')
    
    return render(request, 'admin-templates/editSubject.html', {'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes':selected_intakes})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewSubject(request, subjectCode):
    subject = SubjectTable.objects.get(subjectCode=subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    return render(request, 'admin-templates/viewSubject.html', {'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes':selected_intakes, 'users':selected_users, })

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_activeSubject(request, subjectCode):
    subject = get_object_or_404(SubjectTable, subjectCode=subjectCode) 
    subject.status = "Active"
    subject.save()
    messages.success(request, 'Subject has been activated.')
    return redirect('admin-subject-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_deactiveSubject(request, subjectCode):
    subject = get_object_or_404(SubjectTable, subjectCode=subjectCode) 
    subject.status = "Deactive"
    subject.save()
    messages.success(request, 'Subject has been activated.')
    return redirect('admin-subject-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeSubject(request):
    if request.method == 'POST':
        subjectCode = request.POST['subjectCode']
        subject = get_object_or_404(SubjectTable, subjectCode=subjectCode) 
        folder_path = os.path.join('media', subjectCode)

        # Remove the existing folder and its content
        shutil.rmtree(folder_path, ignore_errors=True)

        subject.delete()
        
        messages.success(request, 'Subject removed successfully.')
        return redirect('admin-subject-management')

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_absenceMonitoringManagement(request):
    limits = AbsenceMonitoringTable.objects.all()
    return render(request, 'admin-templates/absenceMonitoringManagement.html', {'limits': limits})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createAbsenceMonitoring(request):
    if request.method == 'POST':
        absenceLimitName = request.POST['absenceLimitName']
        absenceLimitDays = request.POST['absenceLimitDays']
        adminID = request.POST['adminId']
        if AbsenceMonitoringTable.objects.filter(absenceLimitName=absenceLimitName).exists():
            messages.error(request, 'Absence Limit Name is already in use')
            return redirect('admin-create-absenceMonitoring')

        if AbsenceMonitoringTable.objects.filter(absenceLimitDays=absenceLimitDays).exists():
            messages.error(request, 'Days allowed to absence is already exists')
            return redirect('admin-create-absenceMonitoring')

        try:
            admin_profile_instance = AdminProfile.objects.get(adminId=adminID)
        except AdminProfile.DoesNotExist:
            admin_profile_instance = None 

        AbsenceMonitoringTable.objects.create(absenceLimitName=absenceLimitName, absenceLimitDays=absenceLimitDays, adminID=admin_profile_instance)

        messages.success(request, 'Absence Limit created successfully')
        return redirect('admin-absenceMonitoring-management')

    return render(request, 'admin-templates/createAbsenceMonitoring.html')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editAbsenceMonitoring(request, id):
    limit = AbsenceMonitoringTable.objects.get(id=id)
    if request.method == 'POST':
        absenceLimitName = request.POST['absenceLimitName']
        absenceLimitDays = request.POST['absenceLimitDays']
        adminID = request.POST['adminId']
        if AbsenceMonitoringTable.objects.filter(absenceLimitName=absenceLimitName).exclude(absenceLimitName=absenceLimitName).exists():
            messages.error(request, 'Absence Limit Name is already in use')
            return redirect('admin-create-absenceMonitoring')

        if AbsenceMonitoringTable.objects.filter(absenceLimitDays=absenceLimitDays).exclude(absenceLimitName=absenceLimitName).exists():
            messages.error(request, 'Days allowed to absence is already exists')
            return redirect('admin-create-absenceMonitoring')

        try:
            admin_profile_instance = AdminProfile.objects.get(adminId=adminID)
        except AdminProfile.DoesNotExist:
            admin_profile_instance = None 

        limit.absenceLimitName = absenceLimitName
        limit.absenceLimitDays = absenceLimitDays 
        limit.adminID = admin_profile_instance
        limit.save()

        messages.success(request, 'Absence Limit Modified successfully')
        return redirect('admin-absenceMonitoring-management')
    
    return render(request, 'admin-templates/editAbsenceMonitoring.html', {'limit': limit})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewAbsenceMonitoring(request, id):
    limit = AbsenceMonitoringTable.objects.get(id=id)
    users = UserProfile.objects.filter(absenceMonitoringId = id)
    return render(request, 'admin-templates/viewAbsenceMonitoring.html', {'limit': limit, 'users': users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeAbsenceMonitoring(request):
    if request.method == 'POST':
        intakeCode = request.POST.get('intakeCode')
        intake = get_object_or_404(IntakeTable, intakeCode=intakeCode)
        
        intake.delete()
        
        messages.success(request, 'Intake removed successfully.')
        return redirect('admin-intake-management')

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_leaveManagement(request):
    leaves = LeaveTable.objects.all()
    return render(request, 'admin-templates/leavemanagement.html', {'leaves': leaves})
  
@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_approveLeave(request, id):
    leave = LeaveTable.objects.get(id=id)
    leave.status = "approved"
    leave.save()
    messages.success(request, 'Leave approved')
    return redirect('admin-leave-management')

  
@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_denyLeave(request, id):
    leave = LeaveTable.objects.get(id=id)
    leave.status = "denied"
    leave.save()
    messages.error(request, 'Leave denied')
    return redirect('admin-leave-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewLeave(request, id):
    try:
        leave = LeaveTable.objects.get(id=id)
        return render(request, 'admin-templates/viewLeave.html', {'leave': leave})
    except User.DoesNotExist:
        return render(request, 'error.html', {'message': 'User not found'})
    
@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_attendanceManagement(request):
    attendances = AttendanceTable.objects.all()
    count_userAbsence()
    return render(request, 'admin-templates/attendanceManagement.html', {'attendances':attendances})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_chooseSubject(request):
    subjects = SubjectTable.objects.all()
    if request.method == 'POST':
        subjectCode = request.POST['subjectCode']
        print(subjectCode)
        return redirect('admin-create-attendance', subjectCode=subjectCode)        
    return render(request, 'admin-templates/chooseSubject.html', {'subjects':subjects})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createAttendance(request, subjectCode):
    count_userAbsence()
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

        return redirect('admin-attendance-management')  # Make sure this URL name is defined in your urls.py

    return render(request, 'admin-templates/createAttendance.html', {'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewAttendance(request, id):
    count_userAbsence()
    attendance = AttendanceTable.objects.get(id=id)
    subject = SubjectTable.objects.get(subjectCode=attendance.subjectCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(subject.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)

    # Get a list of attended user IDs
    attended_users_ids = list(attendance.attendedUser.values_list('userId', flat=True))

    return render(request, 'admin-templates/viewAttendance.html', {'attendance': attendance, 'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users, 'attended_users': attended_users_ids})


@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editAttendance(request, id):
    count_userAbsence()
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

        return redirect('admin-attendance-management')  # Make sure this URL name is defined in your urls.py
    return render(request, 'admin-templates/editAttendance.html', {'attendance': attendance, 'subject': subject, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes': selected_intakes, 'users': selected_users, 'attended_users': attended_users_ids})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_reportManagement(request):
    reports = ReportTable.objects.all()
    return render(request, 'admin-templates/reportManagement.html', {'reports': reports})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_readReportView(request, id):
  report = ReportTable.objects.get(id = id)
  if report.status == "delivered" or report.status == "Delivered":
    report.status = "read"
    report.save()
  return redirect ('admin-view-report', id=id)  

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_readReportReply(request, id):
  report = ReportTable.objects.get(id = id)
  if report.status == "delivered" or report.status == "Delivered":
    report.status = "read"
    report.save()
  return redirect ('admin-reply-report', id=id)  

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewReport(request, id):
  report = ReportTable.objects.get(id = id)
  return render(request, 'admin-templates/viewReport.html', {'report':report})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_replyReport(request, id):
    report = ReportTable.objects.get(id = id)
    if request.method == "POST":
        replyMessage = request.POST['replyMessage']
        report.replyMessage = replyMessage
        report.status = "replied"
        report.replyDate = datetime.now()
        report.save()
        return redirect('admin-report-management')
    return render(request, 'admin-templates/replyReport.html', {'report':report})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_notificationManagement(request):
    notifications = NotificationTable.objects.all()
    notificationer = NotificationTable.objects.filter(receiver=request.user.username, status='delivered')
    notification_count = notificationer.count()
    context = {
        'notification_count': notification_count,
        'notifications': notifications,
    }
    return render(request, 'admin-templates/notificationManagement.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_notedNotification(request, id):
  notification = NotificationTable.objects.get(id=id)
  notification.status = "noted"
  notification.save()
  return redirect('admin-notification-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def viewMyProfile_admin(request, user_id):
        if user_id == request.user.id:
            user = User.objects.get(id=user_id)
            admin_user = AdminProfile.objects.get(user = user)
            intakes = IntakeTable.objects.filter(adminId = admin_user.adminId)
            return render(request, 'admin-templates/viewMyProfile_admin.html', {'user': user, 'intakes': intakes, })
        else:
            message = 'Sorry, you are not allowed to view this page'
            return render(request, 'error.html', {'message': message})

def count_userAbsence ():
    students = UserProfile.objects.all()
    for student in students:
        student.absenceMonitoringId = AbsenceMonitoringTable.objects.get(id=1)
        student.save()

    absent_students_count = {}
    for attendance in AttendanceTable.objects.all():
        subject = attendance.subjectCode
        intake_tables = subject.intakeTables.all()
        for intake_table in intake_tables:
            students = UserProfile.objects.filter(intakeCode=intake_table)
            # Get students who are absent
            absent_students = students.exclude(attendance_tables=attendance)
            # Update the absent count for each student
            for student in absent_students:
                if student.userId not in absent_students_count:
                    absent_students_count[student.userId] = {'count': 1, 'triggered': set()}
                else:
                    absent_students_count[student.userId]['count'] += 1
                # Check for triggers
                for limit in AbsenceMonitoringTable.objects.exclude(absenceLimitDays=0):
                    if (
                        absent_students_count[student.userId]['count'] >= limit.absenceLimitDays
                        and limit.absenceLimitDays not in absent_students_count[student.userId]['triggered']
                    ):
                        student.absenceMonitoringId = limit
                        student.save()
                        message = f"Student {student.userId} has triggered {limit.absenceLimitName}"
                        if NotificationTable.objects.filter(notifyMessage = message).exists():
                            break
                        else:
                            user_intake = student.intakeCode.intakeCode
                            intake = IntakeTable.objects.get(intakeCode = user_intake)
                            admin_username = intake.adminId.user.username
                            NotificationTable.objects.create( receiver = admin_username, notifyDate = datetime.now(), notifyMessage = message, status = "delivered")
                            NotificationTable.objects.create( receiver = student.user.username, notifyDate = datetime.now(), notifyMessage = message, status = "delivered")
                            absent_students_count[student.userId]['triggered'].add(limit.absenceLimitDays)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_face (request, user_id):
    if user_id == request.user.id :
        if request.method == "POST":
            subjectCode = request.POST['subjectCode']
            virtualenv_path = "myenv"
            python_path = os.path.join(virtualenv_path, "bin", "python")
            main_script_path = "main.py"
            creator = request.user.username
            command = [python_path, main_script_path, subjectCode, creator]
            try:
                subprocess.run(command, capture_output=True, text=True, shell=False)
            except subprocess.CalledProcessError as e:
                pass

            user_instance = User.objects.get(id = request.user.id)
            if user_instance.groups.exists():
                if user_instance.groups.first().name == 'admin':
                    return redirect('admin-dashboard')
                elif user_instance.groups.first().name == 'lecturer':
                    return redirect('lecturer-dashboard')
                else:
                    return redirect('user-dashboard')
        
        subjects = SubjectTable.objects.all()
        return render(request, 'admin-templates/admin_face.html', {'subjects': subjects})
    else:
        message = 'Sorry, you are not allowed to view this page'
        return render(request, 'error.html', {'message': message})
    
def collect_attendance(processed_names_list, subjectCode, creator):
        subjecter = SubjectTable.objects.get(subjectCode=subjectCode)
        intakes = IntakeTable.objects.all()
        selected_intakes = list(subjecter.intakeTables.values_list('intakeCode', flat=True))
        selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)

        subjectCoder = subjectCode
        creatorer = creator
        attendedUser = processed_names_list
        subject = SubjectTable.objects.filter(subjectCode = subjectCode)
        totalUser = selected_users.count()
        
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
    