import re
from json import JSONDecodeError

import requests
from flask import Blueprint, render_template, request, flash


bp = Blueprint('image', __name__, url_prefix='/image')

@bp.route('/post', methods=('GET', 'POST'))
def post_image():
    if request.method == 'GET':
        return render_template('image_post.html')

    image = request.files['image']
    if not re.match(r".+\.(jpg|jpeg|webp|gif|png)", image.filename.lower()):
        flash("这看起来不像是图片")
        return render_template('image_post.html')

    resp = requests.post("http://127.0.0.1:5001/upload_image", files={'file': (image.filename, image)})

    try:
        flash(f"{resp.json()}, {resp.status_code}")
    except JSONDecodeError:
        flash(f"{resp.text}, {resp.status_code}")
    return render_template('image_post.html')

@bp.get('/get')
def get_image():
    pass
