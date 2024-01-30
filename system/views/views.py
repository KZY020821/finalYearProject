from django.contrib.auth import get_user
from django.db.models import Q
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from ..decorators import unauthenticated_user, allow_users
from datetime import datetime
from django.http import HttpResponse
from ..models import Profile as personalinfo, Attendance as attendanceModel, subject as subjectTable, intake as intakeTable, leave, feedback as feedbackTable, UserProfile, IntakeTable, AbsenceMonitoringTable, LecturerProfile, SubjectTable, AdminProfile
import subprocess
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.storage import FileSystemStorage
import face_recognition
import os, sys
import cv2
import numpy as np
import math

# login
@unauthenticated_user
def forgotPassword(request):
  return render(request, 'forgot-password.html')

@unauthenticated_user
def loginPage(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
    
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            user_instance = User.objects.get(username=username)
            if user_instance.groups.exists():
                if user_instance.groups.first().name == 'admin':
                    messages.success(request, "You have successfully logged in.") 
                    return redirect('admin-dashboard')
                elif user_instance.groups.first().name == 'lecturer':
                    messages.success(request, "You have successfully logged in.") 
                    return redirect('lecturer-dashboard')
                else:
                    messages.success(request, "You have successfully logged in.") 
                    return redirect('user-dashboard')
            else:
                messages.error(request, "You have successfully logged in.") 
                return redirect ('error')
        else:
            messages.error(request, "wrong email or password")
            return redirect("/") 
    else:
        return render(request, 'login.html')

@unauthenticated_user
def registerPage(request):
    if request.method == "POST":
        id = request.POST['studentID']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        intakeCode = request.POST['intakeCode']
        faceimage = request.FILES.get('image')  # Use request.FILES for file input

        if password != password2:
            messages.error(request, "Password not same")
            return redirect('register') 
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect('register') 
        elif User.objects.filter(username=id).exists():
            messages.error(request, "studentID already used")
            return redirect('register') 
        else:
             # Get the username and user ID
            username_id = f"{id}_{first_name}-{last_name}"

            # Determine the file extension based on the user's uploaded file
            file_extension = faceimage.name.split('.')[-1]

            # Define the path to save the image with the appropriate extension
            image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

            # Delete the existing image if it exists
            if os.path.exists(image_path):
                os.remove(image_path)

            # Save the uploaded image with the new name and correct file extension
            fs = FileSystemStorage()
            fs.save(image_path, faceimage)

            try:
                intake_instance = IntakeTable.objects.get(intakeCode=intakeCode)
            except IntakeTable.DoesNotExist:
                intake_instance = None 
            
            try:
                absenceMonitoring_instance = AbsenceMonitoringTable.objects.get(id=1)
            except AbsenceMonitoringTable.DoesNotExist:
                absenceMonitoring_instance = None 
            
            if intake_instance:
                user = User.objects.create_user(username=id , email=email, password=password, first_name=first_name, last_name=last_name)
                user.save()

                user_profile = UserProfile(user=user, userId=id, intakeCode=intake_instance, absenceMonitoringId=absenceMonitoring_instance, faceImageUrl=image_path)
                user_profile.save()

                group = Group.objects.get(name='user')
                user.groups.add(group)

                messages.success(request, "User registered successfully.")
                return redirect("/")
            else: 
                messages.error(request, "register failed.")
                return redirect("register")
            
    else:
        intakes = IntakeTable.objects.all()
        return render(request, 'register.html', {'intakes': intakes})

@login_required(login_url='/')
@allow_users(allow_roles=['admin'])
def editMyProfile(request, user_id):
  try:
      user = User.objects.get(id=user_id)
      if request.method == 'POST':
        userID = request.POST['userID']
        userEmail = request.POST['userEmail']
        firstName = request.POST['first_name']
        lastName = request.POST['last_name']
        username = request.POST['username']
        profileImage = request.FILES.get('image')

        if User.objects.filter(email=userEmail).exclude(id=user_id).exists():
            messages.error(request, 'Email used')
        elif User.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, 'Username used')
        elif UserProfile.objects.filter(userId=userID).exclude(user=user).exists():
            messages.error(request, 'user ID used')
        else:
          user.email = userEmail
          user.first_name = firstName
          user.last_name = lastName
          user.username = username
          user.save()
          
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
      return render(request, 'admin-tamplates/editUser.html', {'user': user})
  except User.DoesNotExist:
      return render(request, 'error_page.html', {'error_message': 'User not found'})

@login_required(login_url='/')
def viewMyProfile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        if user.groups.exists():
            if user.groups.first().name == 'lecturer':
                lecturer_user = LecturerProfile.objects.get(user = user)
                subjects = SubjectTable.objects.filter(lecturerId = lecturer_user.lecturerId)
                return render(request, 'viewMyProfile.html', {'user': user, 'subjects': subjects, })
            elif user.groups.first().name == 'admin':
                admin_user = AdminProfile.objects.get(user = user)
                intakes = IntakeTable.objects.filter(adminId = admin_user.adminId)
                return render(request, 'viewMyProfile.html', {'user': user, 'intakes': intakes, })
            elif user.groups.first().name == 'user':
                normal_user = UserProfile.objects.get(user=user)
                subjects = SubjectTable.objects.filter(intakeTables__intakeCode = normal_user.intakeCode.intakeCode, status = "Active" or "active")
                return render(request, 'viewMyProfile.html', {'user': user, 'subjects': subjects})

        return render(request, 'viewMyProfile.html', {'user': user,})    
        
    except User.DoesNotExist:
      return render(request, 'error_page.html', {'error_message': 'User not found'})

@login_required(login_url='/')
def deleteMyProfile(request, id):
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




# old
@login_required(login_url="/")
def index(request):
    if request.method == "POST":
        classCode = request.POST['classCode']

        # Execute main.py with the classCode as a command-line argument
        command = ["/Users/khorzeyi/code/finalYearProject/myenv/bin/python", "/Users/khorzeyi/code/finalYearProject/main.py", classCode]
        
        try:
            subprocess.run(command, capture_output=True, text=True, shell=False)
            # Handle the subprocess result if needed
        except subprocess.CalledProcessError as e:
            # Handle any errors or exceptions
            pass
            
        currentUserId = request.user.id
        user_instance = User.objects.get(id = currentUserId)
        if user_instance.groups.exists():
            if user_instance.groups.first().name == 'admin':
                return redirect('admin-dashboard')
            elif user_instance.groups.first().name == 'lecturer':
                return redirect('lecturer-dashboard')
            else:
                return redirect('user-dashboard')
        return render(request, 'dashboard.html')

    subjects = subjectTable.objects.all()
    data = {'subjects': subjects}
    return render(request, 'index.html', data)

@login_required(login_url="/")
def attendance(request):
  current_year= datetime.now().year
  current_month= datetime.now().month
  data = User.objects.all()
  context = {'users': data, 'current_year': current_year, 'current_month':current_month}
  return render(request, 'attendance.html', context)

@login_required(login_url="/")
@allow_users(allow_roles=['admin'])
def editProfile(request, user_id=None):
    user_id = request.GET.get('user_id')
    selected_user = get_object_or_404(User, id=user_id) if user_id else request.user
    user = request.user

    if request.method == "POST":
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        intakeCode = request.POST['intakeCode']
        phone_number = request.POST['phone_number']

        if personalinfo.objects.filter(phone_number=phone_number).exclude(user=user).exists():
            messages.error(request, "Phone number already used by another user")
            return redirect('edit-profile', user_id=user.id)

        # Update user information
        selected_user.first_name = first_name
        selected_user.last_name = last_name
        selected_user.save()

        # Update or create profile information
        personalInfo = personalinfo.objects.get(user=selected_user)

        personalInfo.phone_number = phone_number
        personalInfo.intakeCode = intakeCode
        personalInfo.save()
        messages.success(request, "Profile updated successfully")
    intakes = intakeTable.objects.all()
    data = {'intakes': intakes, 'user': user, 'profile': user.profile, 'selected_user': selected_user }
    return render(request, 'edit-profile.html', data)

@login_required(login_url="/")
def profile(request):
  return render(request, 'profile.html')

@login_required(login_url='/')
def logoutUser (request):
    logout(request)
    messages.success(request, 'You have succesfully logged out')
    return redirect('/')
    
@login_required(login_url="/")
@allow_users(allow_roles=['admin'])
def users(request):
  data = User.objects.all()
  return render(request, 'users.html', {'users': data})

def delete_user_image(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        # Assuming user_id is the filename of the image to be deleted
        user = User.objects.get(id=user_id)
        username = user.username
        username_id = f"{username}_{user.id}"
        print(username_id)

        allowed_extensions = ['jpg', 'jpeg', 'png']
        # Attempt to delete the image file for each allowed extension
        for extension in allowed_extensions:
            image_path = os.path.join('/Users/khorzeyi/code/finalYearProject/media/faceImage', f'{username_id}.{extension}')

            if os.path.exists(image_path):
                os.remove(image_path)
        return JsonResponse({'message': 'User deleted successfully'})

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url="/")
@allow_users(allow_roles=['admin'])
def warnings(request):
  data = User.objects.all()
  return render(request, 'warnings.html', {'users': data})

@login_required(login_url="/")
def error(request):
  return render(request, 'error.html')

@login_required(login_url="/")
def deleteUser(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return JsonResponse({'message': 'User deleted successfully'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url="/")
def registerAdmin(request):
    if request.method == "POST":
        # Extract user registration data from the POST request
        studentID = request.POST['studentID']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        intakeCode = request.POST['intakeCode']
        phone_number = request.POST['phone_number']
        faceimage = request.FILES.get('image')  # Use request.FILES for file input

        if password != password2:
            messages.error(request, "Password not same")
            return redirect('register') 
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect('register') 
        elif User.objects.filter(username=studentID).exists():
            messages.error(request, "studentID already used")
            return redirect('register') 
        elif personalinfo.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already used")
            return redirect('register') 
        else:
            # Create a new User instance
            user = User.objects.create_user(username=studentID, email=email, password=password, first_name=first_name, last_name=last_name)
            user.save()
             # Get the username and user ID
            username_id = f"{studentID}_{user.id}"

            # Determine the file extension based on the user's uploaded file
            file_extension = faceimage.name.split('.')[-1]

            # Define the path to save the image with the appropriate extension
            image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

            # Delete the existing image if it exists
            if os.path.exists(image_path):
                os.remove(image_path)

            # Save the uploaded image with the new name and correct file extension
            fs = FileSystemStorage()
            fs.save(image_path, faceimage)

            # Create a new profile instance and associate it with the user
            user_profile = personalinfo(user=user, intakeCode=intakeCode, phone_number=phone_number, image=image_path)
            user_profile.save()

            # Add the user to a group if needed (e.g., 'user' group)
            group = Group.objects.get(name='user')
            user.groups.add(group)

            messages.success(request, "User registered successfully.")
            return redirect("/")  # Redirect to the login page
    else:
        intakes = intakeTable.objects.all()
        data = {'intakes': intakes}
        return render(request, 'registerAdmin.html', data)

@login_required(login_url="/")
def registerUser(request):
    if request.method == "POST":
        # Extract user registration data from the POST request
        studentID = request.POST['studentID']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        intakeCode = request.POST['intakeCode']
        phone_number = request.POST['phone_number']
        faceimage = request.FILES.get('image')  # Use request.FILES for file input

        if password != password2:
            messages.error(request, "Password not same")
            return redirect('register') 
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect('register') 
        elif User.objects.filter(username=studentID).exists():
            messages.error(request, "studentID already used")
            return redirect('register') 
        elif personalinfo.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already used")
            return redirect('register') 
        else:
            # Create a new User instance
            user = User.objects.create_user(username=studentID, email=email, password=password, first_name=first_name, last_name=last_name)
            user.save()
             # Get the username and user ID
            username_id = f"{studentID}_{user.id}"

            # Determine the file extension based on the user's uploaded file
            file_extension = faceimage.name.split('.')[-1]

            # Define the path to save the image with the appropriate extension
            image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")

            # Delete the existing image if it exists
            if os.path.exists(image_path):
                os.remove(image_path)

            # Save the uploaded image with the new name and correct file extension
            fs = FileSystemStorage()
            fs.save(image_path, faceimage)

            # Create a new profile instance and associate it with the user
            user_profile = personalinfo(user=user, intakeCode=intakeCode, phone_number=phone_number, image=image_path)
            user_profile.save()

            # Add the user to a group if needed (e.g., 'user' group)
            group = Group.objects.get(name='user')
            user.groups.add(group)

            messages.success(request, "User registered successfully.")
            return redirect("/")  # Redirect to the login page
    else:
        intakes = intakeTable.objects.all()
        data = {'intakes': intakes}
        return render(request, 'registerUser.html', data)

@login_required(login_url="/")
@allow_users(allow_roles=['admin'])
def reviewLeaves(request):
  data = User.objects.all()
  leaveData = leave.objects.all()
  return render(request, 'reviewLeaves.html', {'users': data, 'leaves': leaveData})

@login_required(login_url="/")
def applyLeaves(request):
    data = User.objects.all()
    leaveData = leave.objects.all()
    if request.method == "POST":
        leaveTitle = request.POST.get('leaveTitle')
        leaveDescription = request.POST.get('leaveDescription')
        startDate = request.POST.get('startDate')
        endDate = request.POST.get('endDate')
        leaveAttachment = request.FILES.get('leaveAttachment')
        user = get_user(request)

        leaves = leave.objects.create(leaveTitle = leaveTitle, leaveDescription = leaveDescription, userID = user.id, startDate = startDate, endDate = endDate, leaveAttachment = leaveAttachment)
        leaves.save
        messages.success(request, "Leave applied, waiting for approval.")
        return render(request, 'applyLeaves.html', {'users': data, 'leaves': leaveData})
    else:
        return render(request, 'applyLeaves.html', {'users': data, 'leaves': leaveData})

@login_required(login_url="/")
@allow_users(allow_roles=['admin'])
def changeImage(request):
    # Get the user to change the image for
    user_to_change = None

    if request.method == "POST":
        user_id = request.GET.get('user_id')

        if user_id is not None:
            try:
                user_to_change = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise Http404("User does not exist")

    # If user_id is not provided, change the image for the currently logged-in user
    if user_to_change is None:
        user_to_change = request.user

    if request.method == "POST":
        # Check if a file was uploaded
        faceimage = request.FILES.get('image')

        if faceimage:
            username_id = f"{user_to_change.username}_{user_to_change.id}"
            file_extension = faceimage.name.split('.')[-1]
            new_image_name = f"{username_id}.{file_extension}"

            # Define the path to save the image in the "faceImage" directory
            image_path = os.path.join('faceImage', new_image_name)

            # Get the existing image path from the user's profile
            existing_image_path = user_to_change.profile.image.path if user_to_change.profile.image else None

            # If an existing image exists, delete it
            if existing_image_path and os.path.exists(existing_image_path):
                os.remove(existing_image_path)

            # Create a new profile instance and associate it with the user
            user_profile, created = personalinfo.objects.get_or_create(user=user_to_change)
            user_profile.image = image_path
            user_profile.save()

            # Save the uploaded image with the desired name and path
            fs = FileSystemStorage(location='media/faceImage', base_url='/media/faceImage/')
            fs.save(new_image_name, faceimage)

            messages.success(request, "User image uploaded successfully")
            return redirect('dashboard')

        else:
            messages.error(request, "No image was uploaded.")

    return render(request, 'changeImage.html')

def save_attendance(name, classCode):
    if name is not None and classCode is not None:
        try:
            attendance = attendanceModel(name=name, attendanceSubjectCode=classCode)
            attendance.save()
        except Exception as e:
            print(f"Error saving attendance: {str(e)}")
    else:
        print("Both name and classCode must be provided.")

def test(request):
    return render(request, 'test.html')

@login_required(login_url="/")
def subject(request):
    data = User.objects.all()
    subject = subjectTable.objects.all()
    if request.method == "POST":
        subjectCode = request.POST.get('subjectCode')
        subjectName = request.POST.get('subjectName')
        lecturerID = request.POST.get('lecturerID')
        intakeCode = request.POST.get('intakeCode')

        subjectData = subjectTable.objects.create( subjectCode= subjectCode, subjectName = subjectName, lecturerID = lecturerID, intakeCode = intakeCode)
        subjectData.save
        messages.success(request, "Subject create successful")
        return render(request, 'subject.html', {'users': data, 'subjectData': subject})
    else:
        return render(request, 'subject.html', {'users': data, 'subjectData': subject})
    
@login_required(login_url="/")
def intake(request):
    data = User.objects.all()
    intakeData = intakeTable.objects.all()
    if request.method == "POST":
        intakeCode = request.POST.get('intakeCode')

        intakeUpload = intakeTable.objects.create(intakeCode = intakeCode)
        intakeUpload.save
        messages.success(request, "Intake has been created.")
        return render(request, 'intake.html', {'users': data, 'intakes': intakeData})
    else:
        return render(request, 'intake.html', {'users': data, 'intakes': intakeData})
    
@login_required(login_url="/")
def contactUs(request):
    data = User.objects.all()
    feedbackData = feedbackTable.objects.all()
    if request.method == "POST":
        feedbackTitle = request.POST.get('feedbackTitle')
        feedbackDescription = request.POST.get('feedbackDescription')
        feedbackAttachment = request.POST.get('feedbackAttachment')
        adminID = request.POST.get('adminID')
        user = get_user(request)

        feedbackUpdate = feedbackTable.objects.create(feedbackTitle = feedbackTitle, feedbackDescription = feedbackDescription, feedbackAttachment = feedbackAttachment, adminID = adminID, userID = user.id)
        feedbackUpdate.save
        messages.success(request, "Feedback has been submitted.")
        return render(request, 'contactUs.html', {'users': data, 'feedbacks': feedbackData})
    else:
        return render(request, 'contactUs.html', {'users': data, 'feedbacks': feedbackData})
    
@login_required(login_url="/")
def reviewFeedback(request):
    data = User.objects.all()
    feedbackData = feedbackTable.objects.all()
    return render(request, 'reviewFeedback.html', {'users': data, 'feedbacks': feedbackData})

@login_required(login_url="/")
def viewWarnings(request):
    data = User.objects.all()
    subject = subjectTable.objects.all()
    if request.method == "POST":
        subjectCode = request.POST.get('subjectCode')
        subjectName = request.POST.get('subjectName')
        lecturerID = request.POST.get('lecturerID')
        intakeCode = request.POST.get('intakeCode')

        subjectData = subjectTable.objects.create( subjectCode= subjectCode, subjectName = subjectName, lecturerID = lecturerID, intakeCode = intakeCode)
        subjectData.save
        messages.success(request, "Subject create successful")
        return render(request, 'subject.html', {'users': data, 'subjectData': subject})
    else:
        return render(request, 'subject.html', {'users': data, 'subjectData': subject})

def camera(request):
    return render(request, 'camera.html')
