import os
import shutil
import subprocess
from datetime import datetime

from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.http import (JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _

from ..decorators import allow_users
from ..models import AbsenceMonitoringTable
from ..models import IntakeTable
from ..models import UserProfile
from ..models import AdminProfile
from ..models import LecturerProfile
from ..models import IntakeTable
from ..models import SubjectTable
from ..models import ClassTable
from ..models import LeaveTable
from ..models import AttendanceTable
from ..models import ReportTable
from ..models import NotificationTable
from ..models import AttendanceStatus
from ..models import FaceImage


from django.shortcuts import redirect
from django.contrib import messages
import face_recognition
import csv

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
            if intake in attendance.classCode.intakeTables.all():
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
    intake_count = IntakeTable.objects.count()
    subject_count = SubjectTable.objects.count()
    class_count = ClassTable.objects.count()
    admin_count = AdminProfile.objects.count()
    lecturer_count = LecturerProfile.objects.count()
    user_count = UserProfile.objects.count()
    context =  {
        'average_percentages': average_percentages, 
        'intake_count' : intake_count,
        'subject_count' : subject_count,
        'class_count' : class_count, 
        'admin_count' : admin_count, 
        'lecturer_count' : lecturer_count, 
        'user_count' : user_count, 
        }

    return render(request, 'admin-templates/dashboard.html', context)

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
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        profileImage = request.FILES.get('image')

        if User.objects.filter(email=adminEmail).exists():
            messages.error(request, 'Email used')
        elif User.objects.filter(username=adminID).exists():
            messages.error(request, 'Username used')
        elif AdminProfile.objects.filter(adminId=adminID).exists():
            messages.error(request, 'Admin ID used')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match')
        else:
            try:
                face_image = face_recognition.load_image_file(profileImage)
                face_encoding = face_recognition.face_encodings(face_image)[0]
            except Exception as ex:
                messages.error(request, f"Failed to detect face from the image you uploaded.")
                return redirect('admin-create-admin')
            
            username_id = f"{adminID}_{firstName}-{lastName}"
            file_extension = profileImage.name.split('.')[-1]
            image_path = os.path.join('adminProfileImage', f"{username_id}.{file_extension}")

            if os.path.exists(image_path):
                os.remove(image_path)

            # Save the uploaded image with the new name and correct file extension
            fs = FileSystemStorage()
            fs.save(image_path, profileImage)

            
            user = User.objects.create_user(username=adminID, email=adminEmail, password=password1, first_name=firstName, last_name=lastName)
            user.save()

            group = Group.objects.get(name='admin')
            user.groups.add(group)
            
            admin_profile = AdminProfile(user=user, adminId=adminID, adminProfileImage=image_path)
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
          
          admin_profile = AdminProfile.objects.get(user=user)

          if profileImage:
            try:
                # Attempt to detect face from the new image
                face_image = face_recognition.load_image_file(profileImage)
                face_encoding = face_recognition.face_encodings(face_image)[0]
            except Exception as ex:
                messages.error(request, "Failed to detect face from the image you uploaded.")
                return redirect('admin-edit-admin', user_id=user_id)
            old_image_path = admin_profile.adminProfileImage.path  # Get the current image path
            # Remove the old image file
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

            # Update user details
            user.email = adminEmail
            user.first_name = firstName
            user.last_name = lastName
            user.username = username
            user.save()

            # Update admin profile details
            adminID = admin_profile.adminId
            
            # Save the new image file
            username_id = f"{adminID}_{firstName}-{lastName}"
            file_extension = profileImage.name.split('.')[-1]
            image_pathway = os.path.join('adminProfileImage', f"{username_id}.{file_extension}")

            fs = FileSystemStorage()
            fs.save(image_pathway, profileImage)

            admin_profile.adminProfileImage = image_pathway
            admin_profile.save()

            messages.success(request, 'Modification has been saved successfully.')
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
    password1 = request.POST['password1']
    password2 = request.POST['password2']
    profileImage = request.FILES.get('image')

    if User.objects.filter(email=lecturerEmail).exists():
        messages.error(request, 'Email used')
    elif User.objects.filter(username=lecturerID).exists():
        messages.error(request, 'Username used')
    elif LecturerProfile.objects.filter(lecturerId=lecturerID).exists():
        messages.error(request, 'Lecturer ID used')
    elif password1 != password2:
        messages.error(request, 'Passwords do not match')
    else:
        try:
            face_image = face_recognition.load_image_file(profileImage)
            face_encoding = face_recognition.face_encodings(face_image)[0]
        except Exception as ex:
            messages.error(request, f"Failed to detect face from the image you uploaded.")
            return redirect('admin-create-lecturer')
        
        username_id = f"{lecturerID}_{firstName}-{lastName}"
        file_extension = profileImage.name.split('.')[-1]
        image_path = os.path.join('lecturerProfileImage', f"{username_id}.{file_extension}")

        if os.path.exists(image_path):
            os.remove(image_path)

        # Save the uploaded image with the new name and correct file extension
        fs = FileSystemStorage()
        fs.save(image_path, profileImage)

            
        user = User.objects.create_user(username=lecturerID, email=lecturerEmail, password=password1, first_name=firstName, last_name=lastName)
        user.save()

        group = Group.objects.get(name='lecturer')
        user.groups.add(group)

        lecturer_profile = LecturerProfile(user=user, lecturerId=lecturerID, lecturerProfileImage=image_path)
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

          
            lecturer_profile = LecturerProfile.objects.get(user=user)

            if profileImage:
                try:
                    # Attempt to detect face from the new image
                    face_image = face_recognition.load_image_file(profileImage)
                    face_encoding = face_recognition.face_encodings(face_image)[0]
                except Exception as ex:
                    messages.error(request, "Failed to detect face from the image you uploaded.")
                    return redirect('admin-edit-lecturer', user_id=user_id)
                old_image_path = lecturer_profile.lecturerProfileImage.path  # Get the current image path
                # Remove the old image file
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            # Update user details
            user.email = lecturerEmail
            user.first_name = firstName
            user.last_name = lastName
            user.username = username
            user.save()


            lecturerID = lecturer_profile.lecturerId
            
            # Save the new image file
            username_id = f"{lecturerID}_{firstName}-{lastName}"
            file_extension = profileImage.name.split('.')[-1]
            image_pathway = os.path.join('lecturerProfileImage', f"{username_id}.{file_extension}")

            fs = FileSystemStorage()
            fs.save(image_pathway, profileImage)

            lecturer_profile.lecturerProfileImage = image_pathway
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
            
            try:
                face_image = face_recognition.load_image_file(faceimage)
                face_encoding = face_recognition.face_encodings(face_image)[0]
            except Exception as ex:
                messages.error(request, f"Failed to detect face from the image you uploaded.")
                return redirect('admin-create-user')

            if intake_instance:

                username_id = f"{id}_{first_name}-{last_name}"
                file_extension = faceimage.name.split('.')[-1]
                image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

                if os.path.exists(image_path):
                    os.remove(image_path)

                # Save the uploaded image with the new name and correct file extension
                fs = FileSystemStorage()
                fs.save(image_path, faceimage)

                user = User.objects.create_user(username=id , email=email, password=password, first_name=first_name, last_name=last_name)
                user.save()

                user_profile = UserProfile(user=user, userId=id, intakeCode=intake_instance, absenceMonitoringId=absenceMonitoring_instance, faceImageUrl=image_path)
                user_profile.save()

                group = Group.objects.get(name='user')
                user.groups.add(group)
                
                selected_intake = IntakeTable.objects.get(intakeCode = intakeCode)
                classes = ClassTable.objects.all()
                for kelas in classes:
                    if selected_intake in kelas.intakeTables.all():
                        username_id = f"{id}_{first_name}-{last_name}"
                        file_extension = faceimage.name.split('.')[-1]
                        image_path = os.path.join(f'{kelas.classCode}', f"{username_id}.{file_extension}")

                        if os.path.exists(image_path):
                            os.remove(image_path)

                        # Save the uploaded image with the new name and correct file extension
                        fs = FileSystemStorage()
                        fs.save(image_path, faceimage)

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
        user_profile = UserProfile.objects.get(user=user)

        if request.method == 'POST':
            userID = request.POST['userID']
            userEmail = request.POST['userEmail']
            firstName = request.POST['first_name']
            lastName = request.POST['last_name']
            username = request.POST['username']
            profileImage = request.FILES.get('image')
            intakeCode = request.POST['intakeCode']
            images = request.FILES.getlist('additional_images')

            if User.objects.filter(email=userEmail).exclude(id=user_id).exists():
                messages.error(request, 'Email used')
            elif User.objects.filter(username=username).exclude(id=user_id).exists():
                messages.error(request, 'Username used')
            elif UserProfile.objects.filter(userId=userID).exclude(user=user).exists():
                messages.error(request, 'User ID used')
            else:
                old_image_path = user_profile.faceImageUrl.path
                old_image_filename = os.path.basename(old_image_path)
                classes = ClassTable.objects.all()

                if intakeCode != user_profile.intakeCode.intakeCode:
                    for kelas in classes:
                        old_folder = f'{kelas.classCode}' if user_profile.intakeCode in kelas.intakeTables.all() else None
                        new_folder = f'{kelas.classCode}' if IntakeTable.objects.get(intakeCode=intakeCode) in kelas.intakeTables.all() else None

                        if old_folder:
                            old_image_path_in_old_folder = os.path.join(old_folder, old_image_filename)
                            
                            if default_storage.exists(old_image_path_in_old_folder):
                                default_storage.delete(old_image_path_in_old_folder)

                        if new_folder:

                            username_id = f"{userID}_{firstName}-{lastName}"
                            file_extension = old_image_filename.split('.')[-1]
                            new_image_path = os.path.join(new_folder, f"{username_id}.{file_extension}")

                            # Check if the new image path is a file before removing
                            if os.path.isfile(new_image_path):
                                os.remove(new_image_path)

                            # Save the uploaded image with the new name and correct file extension
                            fs = FileSystemStorage()
                            fs.save(new_image_path, user_profile.faceImageUrl)


                    # Update the UserProfile model with the new intake code
                    user_profile.intakeCode = IntakeTable.objects.get(intakeCode=intakeCode)
                    user_profile.save()

                if profileImage:
                    try:
                        # Attempt to detect face from the new image
                        face_image = face_recognition.load_image_file(profileImage)
                        face_encoding = face_recognition.face_encodings(face_image)[0]
                    except Exception as ex:
                        messages.error(request, "Failed to detect face from the image you uploaded.")
                        return redirect('admin-edit-lecturer', user_id=user_id)

                    # Remove the old image from the UserProfile folder
                    old_image_path = user_profile.faceImageUrl.path
                    if default_storage.exists(old_image_path):
                        default_storage.delete(old_image_path)

                    # Save the uploaded image with the new name and correct file extension
                    username_id = f"{userID}_{firstName}-{lastName}"
                    file_extension = profileImage.name.split('.')[-1]
                    image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

                    fs = FileSystemStorage()
                    fs.save(image_path, profileImage)
                    
                    user_profile.faceImageUrl = image_path
                    user_profile.save()

                    classes = ClassTable.objects.all()
                    old_image_path = user_profile.faceImageUrl.path
                    old_image_filename = os.path.basename(old_image_path)
                    classes = ClassTable.objects.all()
                
                    for kelas in classes:
                        old_folder = f'{kelas.classCode}' if user_profile.intakeCode in kelas.intakeTables.all() else None
                        new_folder = f'{kelas.classCode}' if IntakeTable.objects.get(intakeCode=intakeCode) in kelas.intakeTables.all() else None

                        if old_folder:
                            old_image_path_in_old_folder = os.path.join(old_folder, old_image_filename)
                            
                            if default_storage.exists(old_image_path_in_old_folder):
                                default_storage.delete(old_image_path_in_old_folder)
                        
                        if new_folder:
                            username_id = f"{userID}_{firstName}-{lastName}"
                            file_extension = old_image_filename.split('.')[-1]
                            new_image_path = os.path.join(new_folder, f"{username_id}.{file_extension}")

                            # Check if the new image path is a file before removing
                            if os.path.isfile(new_image_path):
                                os.remove(new_image_path)

                            # Save the uploaded image with the new name and correct file extension
                            fs = FileSystemStorage()
                            fs.save(new_image_path, user_profile.faceImageUrl)

                if images:
                    for profileImage in images:
                        try:
                            # Attempt to detect face from the new image
                            face_image = face_recognition.load_image_file(profileImage)
                            face_encoding = face_recognition.face_encodings(face_image)[0]
                        except Exception as ex:
                            messages.error(request, "Failed to detect face from the image you uploaded.")
                            return redirect('admin-edit-lecturer', user_id=user_id)

                        # Save the uploaded image with the new name and correct file extension
                        username_id = f"{userID}_{firstName}-{lastName}"
                        file_extension = profileImage.name.split('.')[-1]
                        image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

                        fs = FileSystemStorage()
                        fs.save(image_path, profileImage)
                        
                        user_profile.faceImageUrl = image_path
                        user_profile.save()

                        classes = ClassTable.objects.all()
                        old_image_path = user_profile.faceImageUrl.path
                        old_image_filename = os.path.basename(old_image_path)
                        classes = ClassTable.objects.all()
                    


                        for kelas in classes:
                            new_folder = f'{kelas.classCode}' if IntakeTable.objects.get(intakeCode=intakeCode) in kelas.intakeTables.all() else None
                            image_path = os.path.join(f"{kelas.classCode}", f"{username_id}.{file_extension}")
                            if new_folder:
                                fs = FileSystemStorage()
                                fs.save(image_path, profileImage)
                                face_image_instance = FaceImage.objects.create(image=image_path)
                                user_profile.face_images.add(face_image_instance)




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
        user_profile = UserProfile.objects.get(user=user)
        user_profile_image_path = user.userprofile.faceImageUrl.path
    
        user.delete()


        old_image_filename = os.path.basename(user_profile_image_path)
        classes = ClassTable.objects.all()
    
        for kelas in classes:
            old_folder = f'{kelas.classCode}' if user_profile.intakeCode in kelas.intakeTables.all() else None

            if old_folder:
                old_image_path_in_old_folder = os.path.join(old_folder, old_image_filename)
                
                if default_storage.exists(old_image_path_in_old_folder):
                    default_storage.delete(old_image_path_in_old_folder)
                    
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
    classes = ClassTable.objects.all()
    context = {'subjects': subjects, 'classes': classes}
    return render(request, 'admin-templates/subjectManagement.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createSubject(request):
    if request.method == 'POST':
        subjectCode = request.POST['subjectCode']
        subjectName = request.POST['subjectName']
        if SubjectTable.objects.filter(subjectCode=subjectCode).exists():
            messages.error(request, 'Subject code is already in use')
            return redirect('admin-create-subject')

        subject = SubjectTable.objects.create(subjectCode=subjectCode, subjectName=subjectName, status = 'Active')
        subject.save()

        messages.success(request, 'Subject created successfully')
        return redirect('admin-subject-management')

    return render(request, 'admin-templates/createSubject.html')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editSubject(request, subjectCode):
    subject = SubjectTable.objects.get(subjectCode=subjectCode)
    classes = ClassTable.objects.all()
    context = {'subject': subject, 'classes': classes}
    if request.method == 'POST':
        subjectCoder = request.POST['subjectCode']
        subjectName = request.POST['subjectName']
        
        if SubjectTable.objects.filter(subjectCode=subjectCoder).exclude(subjectCode=subjectCoder).exists():
            messages.error(request, 'Subject code is already in use')
            return redirect('admin-edit-subject')
        
        subject.subjectCode = subjectCoder
        subject.subjectName = subjectName
        subject.save()
        messages.success(request, 'Subject updated successfully')
        return redirect('admin-subject-management')
    return render(request, 'admin-templates/editSubject.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewSubject(request, subjectCode):
    subject = SubjectTable.objects.get(subjectCode=subjectCode)
    context = {'subject': subject}
    return render(request, 'admin-templates/viewSubject.html', context)

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
        subject.delete()
        
        messages.success(request, 'Subject removed successfully.')
        return redirect('admin-subject-management')

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_classManagement(request):
    classes = ClassTable.objects.all()
    context = {'classes': classes}
    return render(request, 'admin-templates/classManagement.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createClass(request):
    intakes = IntakeTable.objects.all()
    subjects = SubjectTable.objects.all()
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    context = {'intakes': intakes, 'lecturers': lecturer_users, 'subjects': subjects}
    
    if request.method == 'POST':
        classCode = request.POST['classCode']
        subjectCode = request.POST['subjectCode']
        lecturerId = request.POST['lecturerId']
        selected_intakes = request.POST.getlist('intakes')
        if ClassTable.objects.filter(classCode=classCode).exists():
            messages.error(request, 'Class code is already in use')
            return redirect('admin-create-class')
        try:
            lecturer_instance = LecturerProfile.objects.get(lecturerId=lecturerId)
        except LecturerProfile.DoesNotExist:
            lecturer_instance = None 

        try:
            subject_instance = SubjectTable.objects.get(subjectCode = subjectCode)
        except SubjectTable.DoesNotExist:
            subject_instance = None

        kelas = ClassTable.objects.create(classCode = classCode, subjectCode = subject_instance, lecturerId = lecturer_instance, status = 'Active')
        kelas.intakeTables.set(IntakeTable.objects.filter(intakeCode__in=selected_intakes))
        
        folder_path = os.path.join('media', classCode)
        os.makedirs(folder_path, exist_ok=True)
        
        for intake_code in selected_intakes:
            users_to_copy = UserProfile.objects.filter(intakeCode=intake_code)
            for user in users_to_copy:
                source_path = os.path.join('media', user.faceImageUrl.name)
                destination_path = os.path.join(folder_path, os.path.basename(user.faceImageUrl.name))
                shutil.copy2(source_path, destination_path)

        kelas.noOfUser = UserProfile.objects.filter(intakeCode__in = kelas.intakeTables.all()).count()
        kelas.save()

        if subject_instance.noOfUser is None:
            subject_instance.noOfUser = 0
        
        subject_instance.noOfUser += kelas.noOfUser
        subject_instance.save()

        messages.success(request, 'Class created successfully')
        return redirect('admin-class-management')

    return render(request, 'admin-templates/createClass.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editClass(request, classCode):
    kelas = ClassTable.objects.get(classCode=classCode)
    intakes = IntakeTable.objects.all()
    subjects = SubjectTable.objects.all()
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    selected_intakes = kelas.intakeTables.all()
    context = {'kelas' : kelas, 'intakes': intakes, 'lecturers': lecturer_users, 'subjects': subjects, 'selected_intakes': selected_intakes, }
    if request.method == 'POST':
        classCoder = request.POST['classCode']
        subjectCode = request.POST['subjectCode']
        lecturerId = request.POST['lecturerId']
        selected_intakes = request.POST.getlist('intakes')
        
        if ClassTable.objects.filter(classCode = classCoder).exclude(classCode = classCoder).exists():
            messages.error(request, 'Class code is already in use')
            return redirect('admin-edit-class')
        try:
            lecturer_instance = LecturerProfile.objects.get(lecturerId=lecturerId)
        except LecturerProfile.DoesNotExist:
            lecturer_instance = None 

        try:
            subject_instance = SubjectTable.objects.get(subjectCode = subjectCode)
        except SubjectTable.DoesNotExist:
            subject_instance = None

        kelas.classCode = classCoder
        kelas.subjectCode = subject_instance
        kelas.lecturerId = lecturer_instance
        kelas.intakeTables.set(IntakeTable.objects.filter(intakeCode__in=selected_intakes))
        kelas.noOfUser = UserProfile.objects.filter(intakeCode__in = kelas.intakeTables.all()).count()
        kelas.save()

        folder_path = os.path.join('media', classCoder)

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

        subject_instance.noOfUser = 0
        subject_instance.save()
        
        selected_intakes = kelas.intakeTables.all()
        userprofile = UserProfile.objects.all()
        for user in userprofile:
            if user.intakeCode in selected_intakes:
                subject_instance.noOfUser +=1

        subject_instance.noOfUser
        subject_instance.save()

        messages.success(request, 'Class updated successfully')
        return redirect('admin-class-management')
    
    return render(request, 'admin-templates/editClass.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewClass(request, classCode):
    kelas = ClassTable.objects.get(classCode=classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(kelas.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    lecturer_group = Group.objects.get(name='lecturer')
    lecturer_users = User.objects.filter(groups=lecturer_group)
    context = {'kelas': kelas, 'lecturers': lecturer_users, 'intakes': intakes, 'selected_intakes':selected_intakes, 'users':selected_users, }
    return render(request, 'admin-templates/viewClass.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_activeClass(request, classCode):
    kelas = get_object_or_404(ClassTable, classCode=classCode) 
    kelas.status = "Active"
    kelas.save()
    messages.success(request, 'Class has been activated.')
    return redirect('admin-class-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_deactiveClass(request, classCode):
    kelas = get_object_or_404(ClassTable, classCode=classCode) 
    kelas.status = "Deactive"
    kelas.save()
    messages.success(request, 'Class has been activated.')
    return redirect('admin-class-management')

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_removeClass(request):
    if request.method == 'POST':
        classCode = request.POST['classCode']
        kelas = get_object_or_404(ClassTable, classCode=classCode) 
        folder_path = os.path.join('media', classCode)

        # Remove the existing folder and its content
        shutil.rmtree(folder_path, ignore_errors=True)
        
        subject = SubjectTable.objects.get(subjectCode = kelas.subjectCode.subjectCode)
        
        if subject.noOfUser is None:
            subject.noOfUser = 0

        subject.noOfUser -= kelas.noOfUser
        subject.save()

        kelas.delete()
        
        messages.success(request, 'Class removed successfully.')
        return redirect('admin-class-management')

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

def createCsv(request):
        response = HttpResponse(content_type = 'text/csv')
        current_date = datetime.now()
        formatted_date = current_date.strftime("%Y%m%d")
        response['Content-Disposition'] = f'attachment; filename={formatted_date}-attendance-report.csv'

        writer = csv.writer(response)

        attendances = AttendanceTable.objects.all()
        status = AttendanceStatus.objects.all()
        
        writer.writerow([
            "Date", 
            "Class Code", 
            "Subject Code", 
            "Subject Name",
            "Lecturer's Name",
            "Check In Time",
            "Status",
            "User's Id", 
            "User's Name",
            ])
        
        for attendance in attendances:
            for state in status:
                if state.relation_id.id == attendance.id:
                    # Assuming state.checkIn is an aware datetime
                    aware_datetime = state.checkIn

                    # Convert UTC time to the desired time zone
                    local_time = timezone.localtime(aware_datetime)

                    formatted_time = local_time.strftime('%H:%M:%S')

                    writer.writerow([
                        f"{attendance.classDate.strftime('%d-%m-%Y')}",
                        attendance.classCode.classCode,
                        attendance.classCode.subjectCode.subjectCode,
                        attendance.classCode.subjectCode.subjectName,
                        f"{attendance.classCode.lecturerId.user.first_name} {attendance.classCode.lecturerId.user.last_name}",
                        formatted_time,
                        state.status, 
                        state.userId.userId, 
                        f"{state.userId.user.first_name} {state.userId.user.last_name}"
                    ])
        return response

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_attendanceManagement(request):
    attendances = AttendanceTable.objects.all()
    count_userAbsence()
    return render(request, 'admin-templates/attendanceManagement.html', {'attendances':attendances})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_chooseSubject(request):
    kelas = ClassTable.objects.all()
    context = {'kelas': kelas}
    if request.method == 'POST':
        classCode = request.POST['classCode']
        return redirect('admin-create-attendance', classCode)        
    return render(request, 'admin-templates/chooseSubject.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_createAttendance(request, classCode):
    count_userAbsence()
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
        'subject': subject,
        }
    if request.method == "POST":
        classCoder = request.POST['classCode']
        creator = request.POST['creator']
        attendedUser = request.POST.getlist('attendedUser')
        totalUser = request.POST['totalUser']
        method = "manual"
        noAttendedUser = len(attendedUser)
        classDate = datetime.now()

        try:
            class_instance = ClassTable.objects.get(classCode = classCoder)
        except ClassTable.DoesNotExist:
            class_instance = None 
        
        attendance_instance = AttendanceTable.objects.create(
            classCode = class_instance,
            creator = creator,
            totalUser = totalUser,
            noAttendedUser = noAttendedUser,
            classDate = classDate,
            method = "Manual"
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


        return redirect('admin-attendance-management')

    return render(request, 'admin-templates/createAttendance.html', context)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_viewAttendance(request, id):
    count_userAbsence()
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
    return render(request, 'admin-templates/viewAttendance.html', context)


@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_editAttendance(request, id):
    count_userAbsence()
    attendance = AttendanceTable.objects.get(id=id)
    kelas = ClassTable.objects.get(classCode = attendance.classCode)
    intakes = IntakeTable.objects.all()
    selected_intakes = list(kelas.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)
    attendance_status = AttendanceStatus.objects.filter(relation_id = attendance.id)
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
        'attendance_status' : attendance_status,
        'intakeTables' : intakeTables,
        'lecturers' : lecturer_users,
        'subjects' : subjects,
        }
    
    name_list = []
    if request.method == "POST":
        student_statuses = {}

        noOfAttendedUser = 0
        attendedUser = []
        for status in attendance_status:
            student_id = status.userId.userId
            status_value = request.POST.get(f"status_{student_id}")
            status.status= status_value.lower()
            if status_value.lower() == 'attended':
                noOfAttendedUser += 1
                attendedUser.append(student_id)
            status.save()

        attendance.attendedUser.set('')
        attendance.save()

        for user in attendedUser:
            user_instance = UserProfile.objects.get(userId = user)
            attendance.attendedUser.add(user_instance)

        attendance.noAttendedUser = noOfAttendedUser
        attendance.save()
        
        return redirect('admin-attendance-management')  # Make sure this URL name is defined in your urls.py
    return render(request, 'admin-templates/editAttendance.html', context)

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

def count_userAbsence():
    students = UserProfile.objects.all()

    for student in students:
        student.absenceMonitoringId = AbsenceMonitoringTable.objects.get(id=1)
        student.save()

    absent_students_count = {}

    for attendance in AttendanceTable.objects.all():
        kelas = attendance.classCode
        intake_tables = kelas.intakeTables.all()

        for intake_table in intake_tables:
            students = UserProfile.objects.filter(intakeCode=intake_table)

            for student in students:
                if student.user.date_joined > attendance.classDate:
                    continue

                # Get students who are absent
                absent_students = students.exclude(attended_user_tables=attendance)

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

                            if NotificationTable.objects.filter(notifyMessage=message).exists():
                                break
                            else:
                                user_intake = student.intakeCode.intakeCode
                                intake = IntakeTable.objects.get(intakeCode=user_intake)
                                admin_username = intake.adminId.user.username
                                NotificationTable.objects.create(
                                    receiver=admin_username,
                                    notifyDate=timezone.now(),
                                    notifyMessage=message,
                                    status="delivered"
                                )
                                NotificationTable.objects.create(
                                    receiver=student.user.username,
                                    notifyDate=timezone.now(),
                                    notifyMessage=message,
                                    status="delivered"
                                )
                                absent_students_count[student.userId]['triggered'].add(limit.absenceLimitDays)

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def admin_face (request, user_id):
    if user_id == request.user.id :
        if request.method == "POST":
            classCode = request.POST['classCode']
            virtualenv_path = "myenv"
            python_path = os.path.join(virtualenv_path, "bin", "python")
            main_script_path = f"/Users/khorzeyi/code/finalYearProject/face_rec-master/face_rec.py"
            creator = request.user.username
            command = [python_path, main_script_path, classCode, creator]
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
        
        kelas = ClassTable.objects.all()
        return render(request, 'admin-templates/admin_face.html', {'kelas': kelas})
    else:
        message = 'Sorry, you are not allowed to view this page'
        return render(request, 'error.html', {'message': message})
    
def collect_attendance(processed_names_list, classCode, creator):
    try:
        class_instance = ClassTable.objects.get(classCode=classCode)
    except ClassTable.DoesNotExist:
        return HttpResponse("Class not found", status=404)

    selected_intakes = list(class_instance.intakeTables.values_list('intakeCode', flat=True))
    selected_users = UserProfile.objects.filter(intakeCode__in=selected_intakes)

    classDate = datetime.now()
    noAttendedUser = len(processed_names_list)
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

    user_ids = [name.split('_')[0] for name in processed_names_list]
    users_dict = UserProfile.objects.in_bulk(user_ids)

    for user_id in user_ids:
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

    for user_id in processed_names_list:
        user = users_dict.get(user_id.split('_')[0])
        if user:
            specific_attendance = AttendanceStatus.objects.get(
                relation_id=relation_instance,
                userId=user,
            )
            specific_attendance.status = 'attended'
            specific_attendance.save()

def admin_change_language(request):
    return render(request, 'admin-templates/change_language.html')