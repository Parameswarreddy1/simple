from django.contrib.auth import authenticate, login
from django.forms import forms
from django.shortcuts import render, redirect
from django.http import HttpResponse, request


def home(request):
    return render(request, "home.html")


def staff(request):
    return render(request, "staff.html")


def Achievements(request):
    return render(request, "achievements.html")


def staff_login(request):
    #if request.method == "POST":
        return render(request, 'staff_login.html')



def Login2(request):
    return render(request, "member_login.html")
