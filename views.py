from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404
import subprocess
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

def upload_excel(request):
    context = {
        "total_urls": 0,
        "completed": False,
        "output_ready": False,
    }

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    input_excel_path = os.path.join(UPLOAD_DIR, "input.xlsx")

    # -------------------------------
    # POST: Upload + Run checker
    # -------------------------------
    if request.method == "POST" and request.FILES.get("file"):

        fs = FileSystemStorage(location=UPLOAD_DIR)

        # overwrite old file if exists
        if os.path.exists(input_excel_path):
            os.remove(input_excel_path)

        fs.save("input.xlsx", request.FILES["file"])

        try:
            df = pd.read_excel(input_excel_path)
            context["total_urls"] = len(df.iloc[:, 0].dropna())
        except Exception:
            context["total_urls"] = 0

        # run checker
        subprocess.run(
            ["python", "url_runner/deep_url_checker.py"],
            cwd=BASE_DIR,
            shell=True
        )

        context["completed"] = True
        context["output_ready"] = os.path.exists(
            os.path.join(OUTPUT_DIR, "url_deep_check_results.xlsx")
        )

    # -------------------------------
    # GET: keep total_urls visible
    # -------------------------------
    elif os.path.exists(input_excel_path):
        try:
            df = pd.read_excel(input_excel_path)
            context["total_urls"] = len(df.iloc[:, 0].dropna())
        except Exception:
            context["total_urls"] = 0

    return render(request, "upload.html", context)


def download_output(request):
    file_path = os.path.join(OUTPUT_DIR, "url_deep_check_results.xlsx")

    if not os.path.exists(file_path):
        raise Http404("Output file not found")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename="url_deep_check_results.xlsx"
    )
