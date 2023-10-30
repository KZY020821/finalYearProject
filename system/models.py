import datetime
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

    def __str__(self):
        return self.subjectCode
    
class intake(models.Model):
    intakeCode = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.intakeCode

class leave(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    )

    leaveID = models.AutoField(primary_key=True)
    userID = models.IntegerField(null=True, default="1")
    leaveTitle = models.CharField(max_length=255)
    leaveDescription = models.CharField(max_length=255, null=True)
    leaveAttachment = models.ImageField(null=True, blank=True, upload_to='leaveAttatchment')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    startDate = models.DateField(default=datetime.date.today)
    endDate = models.DateField(default=datetime.date.today)
    applyDate = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"Leave ID: {self.leaveID}, Title: {self.leaveTitle}"


class Attendance(models.Model):
    name = models.CharField(max_length=255)
    classDate = models.DateTimeField(default=datetime.datetime.now)
    attendanceSubjectCode = models.CharField(max_length=255, null=True, default="Not provided")
    def __str__(self):
        return f"ID:{self.id}, name: {self.name}, date time: {self.classDate}, subject code : {self.attendanceSubjectCode}"