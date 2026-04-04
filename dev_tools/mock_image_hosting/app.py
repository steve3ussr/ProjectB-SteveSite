import os
import re
from flask import Flask, request, url_for, send_from_directory, abort
from nanoid import generate
from PIL import Image


app = Flask(__name__, static_folder='/')
UPLOAD_FOLDER = 'images'


def image_thumbnail(uuid, filename_original):
    width_conf = {'small': 200,
                  'medium': 500,
                  'large': 1024}
    res = {}
    file_path = os.path.join(UPLOAD_FOLDER, filename_original)

    with Image.open(file_path) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
        w, h = img.size

        for thumb_type, thumb_width in width_conf.items():
            if w < thumb_width:
                continue

            ratio = thumb_width / float(w)
            thumb_height = int(ratio * float(h))

            resized_img = img.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            filename_thumb = f"{uuid}_{thumb_type}.webp"
            resized_img.save(os.path.join(UPLOAD_FOLDER, filename_thumb),
                             'WEBP',
                             quality=80,
                             method=6)
            res[thumb_type] = url_for('static', filename=filename_thumb, _external=True)

    return res

def gen_id(filetype):
    uuid = generate(size=8)
    if os.path.exists(os.path.join(UPLOAD_FOLDER, f"uuid.{filetype}")):
        return gen_id(filetype)
    return uuid

def save_file(file, filetype, uuid):
    # save original
    filename_original = f"{uuid}.{filetype}"
    file.save(os.path.join(UPLOAD_FOLDER, filename_original))
    res = {'original': url_for('static', filename=filename_original, _external=True)}

    # get thumb
    res.update(image_thumbnail(uuid, filename_original))
    return res

@app.post('/upload_image')
def mock_upload_image():
    file = request.files.get('file')
    if not file:
        return {}, 500

    try:
        img = Image.open(file)
        img.verify()
    except:
        return {'type_error': 'not image'}, 500
    file.seek(0)

    filetype = 'jpg'
    if _ := re.match("^.+\.(.+)$", file.filename):
        filetype = _.group(1).lower()

    # nanoid
    uuid = gen_id(filetype)
    res = save_file(file, filetype, uuid)
    return res, 200

@app.get('/<filename>')
def mock_get_image(filename):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    if not os.path.exists(file_path):
        return abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe_filename)

