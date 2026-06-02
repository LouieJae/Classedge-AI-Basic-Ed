# central_content/views/auth.py
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.shortcuts import render

from central_content.auth_backends import CentralStaffAuthBackend


def login_view(request):
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        backend = CentralStaffAuthBackend()
        user = backend.authenticate(request, email=email, password=password)
        if user:
            user.backend = "central_content.auth_backends.CentralStaffAuthBackend"
            login(request, user)
            return HttpResponseRedirect("/")
        error = "Invalid email or password"
    return render(request, "central_content/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/login")
