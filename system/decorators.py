from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from datetime import datetime, time
from django.http import HttpResponseForbidden
from django.contrib import messages


def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:

            if request.user.groups.exists:
                group = request.user.groups.first().name
                if group == 'admin':
                    messages.success(request, 'You have already logged in')
                    return redirect ('admin-dashboard')
                elif group == 'lecturer':
                    messages.success(request, 'You have already logged in')
                    return redirect ('lecturer-dashboard')
                else:
                    messages.success(request, 'You have already logged in')
                    return redirect ('user-dashboard')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func

def allow_users(allow_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            group = None
            if request.user.groups.exists():
                group = request.user.groups.all()[0].name

            if group in allow_roles:
                return view_func(request, *args, **kwargs)
            else:
                message = 'Sorry, you are not allowed to view this page'
                return render(request, 'error.html', {'message': message})

        return wrapper_func
    return decorator