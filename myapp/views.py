from django.shortcuts import render
from django.http import HttpResponse, request


def home(request):
    return render(request, "home.html")


def staff(request):
    return render(request, "staff.html")


def Achievements(request):
    return render(request, "achievements.html")


def Login1(request):
    return render(request, "staff login.html")
