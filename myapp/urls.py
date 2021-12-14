from django.urls import path

from college import views

urlpatterns = [
    path('',views.home, name="home"),
    path("stf",views.staff, name="staff"),
    path('ach', views.Achievements, name="Achievements"),
    path('port', views.portal, name="portal"),

    ]
