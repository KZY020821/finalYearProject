# Generated by Django 4.2.6 on 2024-02-05 06:45

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0002_remove_attendancestatus_checkin'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancestatus',
            name='checkIn',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
    ]
