from flask import Flask, render_template, redirect, request
from pdf2image import convert_from_path
from PIL import Image
from fpdf import FPDF

import os
import uuid
import base64
import re
import glob

app = Flask(__name__)
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/extract', methods=['POST'])
def extract():
    if 'source_file' not in request.files:
        flash('No img file')
        return redirect(request.url)
    uploaded_file = request.files['source_file']
    request_id = str(uuid.uuid4())
    base_path = os.path.join('static', 'uploads', request_id)
    os.mkdir(base_path)
    pdf_file = os.path.join(base_path, uploaded_file.filename)
    uploaded_file.save(pdf_file)
    pages = convert_from_path(os.path.join(base_path, uploaded_file.filename), 1000)
    filename = ""
    for i, page in enumerate(pages):
        filename = os.path.join(base_path, "%d.png" % i)
        page.save(filename, "PNG")
        filename = os.path.join('uploads', request_id, "%d.png" % i)
    os.unlink(pdf_file)
    return render_template('extract.html', required_image=filename, request_id=request_id)


@app.route('/finalize', methods=['POST'])
def get_image():
    image_b64 = request.values['imageBase64']
    image_data = re.sub('^data:image/.+;base64,', '', image_b64)
    img_data = base64.b64decode(image_data)
    required_image = os.path.join('static', request.values['required_image'])
    with open(required_image, 'wb') as f:
        f.write(img_data)
    pdf = FPDF()
    request_id = request.values['request_id']
    base_path = os.path.join('static', 'uploads', request_id)
    images = glob.glob(os.path.join(base_path, "*.png"))
    images = sorted(images)
    for imageFile in images:
        cover = Image.open(imageFile)
        width, height = cover.size

        # convert pixel in mm with 1px=0.264583 mm
        width, height = float(width * 0.264583), float(height * 0.264583)
        # given we are working with A4 format size
        pdf_size = {'P': {'w': 210, 'h': 297}, 'L': {'w': 297, 'h': 210}}

        # get page orientation from image size
        orientation = 'P' if width < height else 'L'

        #  make sure image size is not greater than the pdf format size
        width = width if width < pdf_size[orientation]['w'] else pdf_size[orientation]['w']
        height = height if height < pdf_size[orientation]['h'] else pdf_size[orientation]['h']

        pdf.add_page(orientation=orientation)

        pdf.image(imageFile, 0, 0, width, height)
    pdf.output(os.path.join(base_path, 'final.pdf'), "F")
    return ''


if __name__ == '__main__':
    app.run(port=8081, debug=True)
