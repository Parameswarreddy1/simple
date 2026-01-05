from django.urls import path
from .views import upload_excel, download_output

from django.urls import path
from .views import upload_excel

urlpatterns = [
    path("", upload_excel, name="upload_excel"),
    path("download/", download_output, name="download_output"),
]