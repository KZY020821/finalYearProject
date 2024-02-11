from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from ..decorators import unauthenticated_user, allow_users
from ..models import UserProfile, IntakeTable, AbsenceMonitoringTable, LecturerProfile, SubjectTable, AdminProfile
from django.core.files.storage import FileSystemStorage
import face_recognition
import os
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
            try:
                validate_password(password, user=None, password_validators=None)
            except ValidationError as e:
                for error_message in e.messages:
                    messages.error(request, error_message)
                return redirect('register')

            try:
                face_image = face_recognition.load_image_file(faceimage)
                face_encoding = face_recognition.face_encodings(face_image)[0]
            except Exception as ex:
                messages.error(request, f"Failed to detect face from the image you uploaded.")
                return redirect('register')

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
def logoutUser (request):
    logout(request)
    messages.success(request, 'You have succesfully logged out')
    return redirect('/')

@login_required(login_url="/")
def error(request):
  return render(request, 'error.html')



