import os
from flask import Flask, request, render_template, send_from_directory
from pptx import Presentation

# Optional: install python-pptx, pillow
# pip install flask python-pptx pillow

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
SLIDES_FOLDER = "static/slides"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SLIDES_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ppt_file = request.files["pptx"]
        if ppt_file and ppt_file.filename.endswith(".pptx"):
            filepath = os.path.join(UPLOAD_FOLDER, ppt_file.filename)
            ppt_file.save(filepath)

            # Convert PPTX → images (requires libreoffice/unoconv OR aspose or similar tool)
            # Simpler: python-pptx cannot render directly, so we use "unoconv" via system call
            output_dir = os.path.abspath(SLIDES_FOLDER)
            os.system(f'libreoffice --headless --convert-to png --outdir "{output_dir}" "{filepath}"')

            # Collect converted slides
            slides = sorted([f for f in os.listdir(SLIDES_FOLDER) if f.endswith(".png")])

            return render_template("viewer.html", slides=slides)

    return render_template("index.html")

@app.route("/slides/<filename>")
def serve_slide(filename):
    return send_from_directory(SLIDES_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)