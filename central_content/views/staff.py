# central_content/views/staff.py
from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content.models import CentralStaff
from central_content.permissions import central_role_required


class CentralStaffCreateForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=CentralStaff.Role.choices)
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)


class CentralStaffEditForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=CentralStaff.Role.choices)
    is_active = forms.BooleanField(required=False)


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_list(request):
    staff = CentralStaff.objects.all()
    return render(request, "central_content/staff/list.html", {"staff": staff})


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_create(request):
    if request.method == "POST":
        form = CentralStaffCreateForm(request.POST)
        if form.is_valid():
            CentralStaff.objects.create_user(
                email=form.cleaned_data["email"],
                full_name=form.cleaned_data["full_name"],
                password=form.cleaned_data["password"],
                role=form.cleaned_data["role"],
            )
            return HttpResponseRedirect("/staff/")
    else:
        form = CentralStaffCreateForm()
    return render(request, "central_content/staff/form.html",
                  {"form": form, "target": None})


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_edit(request, staff_id: int):
    target = get_object_or_404(CentralStaff, pk=staff_id)
    if request.method == "POST":
        form = CentralStaffEditForm(request.POST)
        if form.is_valid():
            target.email = form.cleaned_data["email"]
            target.full_name = form.cleaned_data["full_name"]
            target.role = form.cleaned_data["role"]
            target.is_active = form.cleaned_data["is_active"]
            target.save()
            return HttpResponseRedirect("/staff/")
    else:
        form = CentralStaffEditForm(initial={
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
        })
    return render(request, "central_content/staff/form.html",
                  {"form": form, "target": target})
