from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    return render(request, "home.html")


def staff(request):
    return render(request, "staff.html")


def Achievements(request):
    return render(request, "achievements.html")


def portal(request):
    return render(request, "portal.html")
