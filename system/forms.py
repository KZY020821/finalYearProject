from django import forms
from django.forms import ModelForm
from .models import Profile as personalinfo

class registerForm(ModelForm):
    class Meta:
        model = personalinfo
        # fields = "__all__"
        fields = ''
