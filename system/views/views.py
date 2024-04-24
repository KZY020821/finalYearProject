import datetime as dt
from datetime import datetime
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
from ..models import ReportTable
from json import dump

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
                face_encoding = face_recognition.face_encodings(face_image, model='large')[0]
            except Exception as ex:
                messages.error(request, "Failed to detect face from the image you uploaded.")
                return redirect('admin-create-user')
            
            username_id = f"{id}_{first_name}-{last_name}"
            json_dir = '/Users/khorzeyi/code/finalYearProject/media/encode_faces'
            json_file_path = os.path.join(json_dir, f'{username_id}.json')
                    
            os.makedirs(json_dir, exist_ok=True)
            jsonStatus = {
                'file_name': username_id,
                'face_encoding': face_encoding.tolist()  # Convert NumPy array to list
            }
            with open(json_file_path, 'w') as json_file:
                dump(jsonStatus, json_file)

            file_extension = faceimage.name.split('.')[-1]
            image_path = os.path.join('faceImage', f"{username_id}.{file_extension}")
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
def logoutUser (request):
    logout(request)
    messages.success(request, 'You have succesfully logged out')
    return redirect('/')

@login_required(login_url="/")
def error(request):
  return render(request, 'error.html')

def reportAttendance(request):
    admins = AdminProfile.objects.all()
    context = {'admins': admins}
    
    if request.method == "POST":
        id = request.POST['id']
        adminId = request.POST['adminId']
        classCode = request.POST['classCode']
        reportAttachment = request.FILES['image']
        current_date = dt.datetime.now().strftime("%Y-%m-%d")
        current_time = dt.datetime.now().strftime("%H:%M:%S")
        
        try:
            user = UserProfile.objects.get(userId=id)
        except UserProfile.DoesNotExist:
            messages.error(request, 'ID does not exit')
            return redirect('reportAttendance')
        
        try:
            adminId_instance = AdminProfile.objects.get(adminId=adminId)
        except AdminProfile.DoesNotExist:
            adminId_instance = None 
        reportMessage = f"Hi {adminId_instance.user.first_name} {adminId_instance.user.last_name}, I am {user.user.first_name} {user.user.last_name}. I would like to report that I have attended {classCode} class on {current_date} at {current_time}, but the BOLF-FRAS could not recognize me."
        report = ReportTable.objects.create(
            reportMessage = reportMessage,
            creator = id,
            receiver = adminId_instance,
            reportDate = datetime.now(),
            reportAttachment = reportAttachment
        )
        messages.success(request, 'Report has been created and will be review by your admin.')
        return redirect('reportAttendance')
    return render(request, 'report_attendance.html', context)


