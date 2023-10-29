# Generated by Django 4.2.6 on 2023-10-29 08:32

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('classDate', models.DateTimeField(default=datetime.datetime.now)),
                ('attendanceSubjectCode', models.CharField(default='Not provided', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subjectCode', models.CharField(max_length=255, unique=True)),
                ('subjectName', models.CharField(default='Not provided', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], default='Not provided', max_length=10)),
                ('birthday', models.DateField(default=datetime.date.today)),
                ('phone_number', models.CharField(default='Not provided', max_length=15)),
                ('address', models.CharField(default='Not provided', max_length=255)),
                ('image', models.ImageField(blank=True, default='faceImage/default.png', null=True, upload_to='faceImage')),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
