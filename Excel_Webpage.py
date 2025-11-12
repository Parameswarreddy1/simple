from flask import Flask, request, render_template_string
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Excel Uploader</title>
    <!-- Bootstrap 5 CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Poppins', sans-serif;
        }
        .upload-card {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 450px;
            text-align: center;
        }
        .upload-card h2 {
            color: #333;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .file-input {
            margin-top: 20px;
        }
        .btn-upload {
            background-color: #007bff;
            border: none;
            padding: 10px 25px;
            color: white;
            border-radius: 5px;
            font-weight: 500;
            margin-top: 15px;
            transition: 0.3s;
        }
        .btn-upload:hover {
            background-color: #0056b3;
        }
        .alert {
            margin-top: 20px;
        }
    .custom-heading {
    color: #0000FF !important;              /* Blue text */
    margin-bottom: 25px;
    font-weight: 600;
    letter-spacing: 1px;
    border: 2px solid #000000 !important;   /* Force black border */
    padding: 10px 20px;
    display: inline-block;
    border-radius: 10px;
    background-color: #ffffff;              /* White background so border stands out */
    box-shadow: 0 0 10px rgba(0,0,0,0.1);   /* Optional soft shadow */
}
    </style>
</head>
<body>
    <div class="upload-card">
        <h3 class = "custom-heading">Hii Parameswar</h3>
        <h2>📊 Upload Your Excel File</h2>
        <p class="text-muted">Choose a .xls or .xlsx file to continue</p>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" class="form-control file-input" name="excel_file" accept=".xlsx,.xls" required>
            <button type="submit" class="btn btn-upload">Upload File</button>
        </form>

        {% if message %}
            <div class="alert alert-{{ 'success' if success else 'danger' }}" role="alert">
                {{ message }}
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    message = None
    success = False
    if request.method == 'POST':
        file = request.files.get('excel_file')
        if not file or file.filename == '':
            message = "Please select a valid Excel file."
        else:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            message = f"✅ File '{file.filename}' uploaded successfully!"
            success = True
    return render_template_string(HTML_TEMPLATE, message=message, success=success)

if __name__ == '__main__':
    app.run(debug=True)
