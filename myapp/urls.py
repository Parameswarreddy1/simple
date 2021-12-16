from django.urls import path

from myapp import views

urlpatterns = [
    path('',views.home, name="home"),
    path("stf",views.staff, name="staff"),
    path('ach', views.Achievements, name="Achievements"),
    path('staff login', views.Login1, name="login1"),

    ]
