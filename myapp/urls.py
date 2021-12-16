from django.urls import path

from myapp import views

urlpatterns = [
    path('',views.home, name="home"),
    path("stf",views.staff, name="staff"),
    path('ach', views.Achievements, name="Achievements"),
    path('staff login', views.staff_login, name="login1"),
    path('member_login', views.Login2, name="login2")

    ]
