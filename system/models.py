import datetime
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    intakeCode = models.CharField(max_length=255, default="Not provided")
    phone_number = models.CharField(max_length=15, default='Not provided')
    image = models.ImageField(null=True, blank=True, upload_to='faceImage', default='faceImage/default.png')

    def __str__(self):
        return str(self.user.username)
    
class subject(models.Model):
    subjectCode = models.CharField(max_length=255, unique=True)
    subjectName = models.CharField(max_length=255, default='Not provided')
    lecturerID = models.CharField(max_length=255, default='Not provided')
    intakeCode = models.CharField(max_length=255, default='Not provided')
    def __str__(self):
        return self.subjectCode
    
class intake(models.Model):
    intakeCode = models.CharField(max_length=255, unique=True)
    coordinatorID = models.CharField(max_length=255, null = True, default = "Not provided")
    def __str__(self):
        return self.intakeCode

class leave(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    )

    leaveID = models.AutoField(primary_key=True, default="1")
    userID = models.IntegerField(null=True, default="1")
    leaveTitle = models.CharField(max_length=255)
    leaveDescription = models.CharField(max_length=255, null=True)
    leaveAttachment = models.ImageField(null=True, blank=True, upload_to='leaveAttatchment')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    startDate = models.DateField(default=datetime.date.today)
    endDate = models.DateField(default=datetime.date.today)
    applyDate = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"Leave ID: {self.leaveID}, Title: {self.leaveTitle}, ID {self.userID}"


class Attendance(models.Model):
    name = models.CharField(max_length=255)
    classDate = models.DateTimeField(default=datetime.datetime.now)
    attendanceSubjectCode = models.CharField(max_length=255, null=True, default="Not provided")
    def __str__(self):
        return f"ID:{self.id}, name: {self.name}, date time: {self.classDate}, subject code : {self.attendanceSubjectCode}"
    
class feedback(models.Model):
    feedbackTitle = models.CharField(max_length=255)
    feedbackDescription = models.CharField(max_length=2550)
    feedbackAttachment = models.ImageField(null=True, blank=True, upload_to='feedbackAttachment')
    userID = models.CharField(max_length=255, null=True, default="Not provided")
    adminID = models.CharField(max_length=255, null=True, default="Not provided")
    reply = models.CharField(max_length=2550, null=True, default="Not provided")
    def __str__(self):
        return f"feedbackID:{self.id}, feedbackTitle: {self.feedbackTitle}, From: {self.userID}, To: {self.adminID}"
    
class LecturerProfile(models.Model):
    lecturerId = models.CharField(max_length=50, primary_key=True, default="Not provided")
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'lecturer'})
    lecturerProfileImage = models.ImageField(null=True, blank=True, upload_to='lecturerProfileImage', default='lecturerProfileImage/default.png')
    
    def __str__(self):
        return f"Lecturer ID: {self.lecturerId}, Lecturer Name: {self.user.username}"

class AdminProfile(models.Model):
    adminId = models.CharField(max_length=50, primary_key=True, default="Not provided")
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'admin'})
    adminProfileImage = models.ImageField(null=True, blank=True, upload_to='adminProfileImage', default='adminProfileImage/default.png')
    
    def __str__(self):
        return f"Admin ID: {self.adminId}, Admin name: {self.user.username}"

class IntakeTable(models.Model):
    intakeCode = models.CharField(max_length=255, primary_key=True, default="Not provided")
    adminId = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, default="Not provided")
    
    def __str__(self):
        return f"intake code: {self.intakeCode}, admin ID: {self.adminId}"     
class AbsenceMonitoringTable(models.Model):
    absenceLimitName = models.CharField(max_length=255, default = "Not provided")
    absenceLimitDays = models.IntegerField(default = 1)
    adminID = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, default = "Not provided")
    def __str__(self):
        return f"ID: {self.id}, Name: {self.absenceLimitName}, Day(s): {self.absenceLimitDays}, Set by {self.adminID}"
class UserProfile(models.Model):
    userId = models.CharField(max_length=50, primary_key=True, default="Not provided")
    intakeCode = models.ForeignKey(IntakeTable, on_delete=models.CASCADE, default="Not provided")
    absenceMonitoringId = models.ForeignKey(AbsenceMonitoringTable, on_delete=models.SET_NULL, null=True, blank=True)
    faceImageUrl = models.ImageField(null=True, blank=True, upload_to='faceImage', default='faceImage/default.png')
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'user'})
    
    def __str__(self):
        return f"User ID: {self.userId}, intake code: {self.intakeCode}, username {self.user.username}"
class SubjectTable(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('deactive', 'Deactive'),
    )
    subjectCode = models.CharField(max_length=50, primary_key=True, default="Not provided")
    lecturerId = models.ForeignKey(LecturerProfile, on_delete=models.CASCADE, default="Not provided")
    intakeTables = models.ManyToManyField('IntakeTable', related_name='subjects', blank=True)
    subjectName = models.CharField(max_length=50, default="Not provided")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    noOfUser = models.IntegerField(default=0)

    def __str__(self):
        return self.subjectCode
    
class LeaveTable(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    )
    userID = models.ForeignKey(UserProfile, on_delete=models.CASCADE, default = "Not provided")
    adminID = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, default="Not provided")
    leaveTitle = models.CharField(max_length=255, default = "Not provided")
    leaveDescription = models.CharField(max_length=255, null=True)
    leaveAttachment = models.ImageField(null=True, blank=True, upload_to='leaveAttatchment')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    startDate = models.DateField(default=datetime.date.today)
    endDate = models.DateField(default=datetime.date.today)
    applyDate = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"Leave ID: {self.id}, Title: {self.leaveTitle}, ID {self.userID}"

class AttendanceTable(models.Model):
    subjectCode = models.ForeignKey(SubjectTable, on_delete=models.CASCADE, default="Not provided")
    creator = models.CharField(max_length=255, default="Not provided")
    attendedUser = models.ManyToManyField('UserProfile', related_name='attendance_tables', blank=True)
    noAttendedUser= models.IntegerField(default=0)
    totalUser = models.IntegerField(default=0)
    classDate = models.DateTimeField(default=datetime.datetime.now)
    def __str__(self):
        return f"ID:{self.id}, date time: {self.classDate}, subject code : {self.subjectCode}"
    
class ReportTable(models.Model):
    TITLE_CHOICES = (
        ('User Experience', 'user experience'),
        ('Attendance', 'attendance'),
        ('Others', 'others'),
    )
    STATUS_CHOICES = (
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),
    )
    reportTitle = models.CharField(max_length=50, choices=TITLE_CHOICES, default='Attendance')
    reportMessage = models.CharField(max_length=255, default="Not provided")
    creator = models.CharField(max_length=255, default="Not provided")
    reportDate = models.DateTimeField(default=datetime.datetime.now)
    receiver = models.ForeignKey(AdminProfile, on_delete=models.CASCADE, default="Not provided")
    replyMessage = models.CharField(max_length=255, default="Not provided", blank=True, null = True)
    replyDate = models.DateTimeField(default=datetime.datetime.now, blank =True, null = True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='delivered')

    def __str__(self):
        return f"ID:{self.id}"
    
class NotificationTable(models.Model):
    STATUS_CHOICES = (
        ('delivered', 'Delivered'),
        ('noted', 'Noted'),
    )
    receiver = models.CharField(max_length=255, default="Not provided")
    notifyDate = models.DateTimeField(default=datetime.datetime.now)
    notifyMessage = models.CharField(max_length=255, default="Not provided")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='delivered')

    def __str__(self):
        return f"ID:{self.id}"