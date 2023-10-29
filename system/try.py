import datetime
from django.contrib.auth.models import User
from django.db import models

class profile(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], default='Not provided')
    birthday = models.DateField(default=datetime.date.today)
    phone_number = models.CharField(max_length=15, default='Not provided')
    address = models.CharField(max_length=255, default='Not provided')
    image = models.ImageField(null=True, blank=True, upload_to='faceImage', default='faceImage/default.png')

    def __str__(self):
        return str(self.user.username)
    
class Attendance(models.Model):
    name = models.CharField(max_length=255)