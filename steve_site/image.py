import io
import nanoid
from PIL import Image, UnidentifiedImageError
from flask import Blueprint, request, current_app, jsonify, session, g
from steve_site.auth import force_login
from datetime import datetime
from steve_site.db_api import db_open


bp = Blueprint('image', __name__, url_prefix='/image')


def get_chopped_high_img(img):
    # chop from top, make w:h=3:4
    w, h = img.size

    left = 0
    right = w
    top = 0
    bottom = int(w * (4 / 3))

    return img.crop((left, top, right, bottom))


def get_chopped_wide_img(img):
    # chop from center, make w:h=4:3
    w, h = img.size

    target_w = int(h / 3 * 4)
    center_x = w//2
    left = center_x - target_w
    right = center_x + target_w
    top = 0
    bottom = h

    return img.crop((left, top, right, bottom))


def get_resized_img(src, resize_edge, target_size):
    w, h = src.size
    if resize_edge == 'w':
        w, h = target_size, int(h * target_size / w)
    else:
        w, h = int(w * target_size / h), target_size

    if w > 16383:
        w, h = 16383, int(16383 * h / w)
    elif h > 16383:
        w, h = int(16383 * w / h), 16383
    return src.resize((w, h), Image.Resampling.LANCZOS)


@bp.post('/post')
@force_login
def post_image():
    image_file = request.files['image']
    image_bytes = image_file.read()

    # step 1: block > 15MB
    if len(image_bytes) > 15_000_000:
        return jsonify({"error": "上传失败：图片大小超过 15MB 限制"}), 500

    # step 2: check if user image count reach limit
    g.uid = session.get('uid', None)
    if g.uid is None:
        return jsonify({"error": "无用户登录状态信息"}), 500
    g.con = db_open()
    _ = g.con.execute("SELECT level FROM user WHERE id=?", (g.uid,)).fetchone()
    level = _['level']
    if level == 'Admin':
        limit = 1000
    elif level == 'Operator':
        limit = 500
    else:
        limit = 200
    cnt = g.con.execute("SELECT COUNT(id) FROM image WHERE user_id = ? AND status = 'ACTIVE'", (g.uid,)).fetchone()
    current_app.logger.info(f"{cnt=}")

    if cnt['COUNT(id)'] >= limit:
        return jsonify({"error": f"图床使用量已达上限{limit}"}), 500

    # step 3: block non-image
    stream = io.BytesIO(image_bytes)
    try:
        img = Image.open(stream)
    except UnidentifiedImageError as e:
        return jsonify({"error": "上传失败：文件不是合法的图片格式!"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexcepted error: {e}"}), 500

    # step 4: block > 20MP
    w, h = img.size
    if w * h > 20_000_000:
        return jsonify({"error": "上传失败：图片分辨率超过 20MP 限制. 如果是超长截图, 建议将其裁剪拆分为 2-3 张图片分别上传, 这样阅读体验会更好哦!"}), 500

    # step 5: get upload res
    try:
        g.image_uuid = nanoid.generate(size=8)
        res = upload_and_resize_image(img)
        current_app.logger.info(f"{res=}")
        """
            res be like: 
            res = {'thumb': {'url': 'http://r2.com/djhrpvw_thumb.webp', 'width': 200, 'height': 150, 'size': 2885}, 
                   'small': {'url': 'http://r2.com/djhrpvw_small.webp', 'width': 600, 'height': 450, 'size': 12885},
                   'large': {'url': 'http://r2.com/djhrpvw_large.webp', 'width': 1200, 'height': 800, 'size': 202885}}
            res might contain 'error': 'error occurred when uploading thumb: *detail*'
        """
        size_sum = sum([info['size'] for info in res.values()])
        current_app.logger.info(f"{size_sum=}")
        g.con.execute("INSERT INTO image(uuid, image_cnt, file_size, user_id, url_and_size) "
                      "VALUES(?, ?, ?, ?, ?)",
                      (g.image_uuid, len(res), size_sum, g.uid, res))
        g.con.commit()
        return jsonify(res), 200

    except Exception as e:
        return jsonify({"error": f"Unexcepted error when uploading: {e}"}), 500


resize_target_type = ('thumb', 'small', 'large')
resize_target_size = {'normal': (200, 600, 1200),
                      'extreme': (200, 300, 600)}


def upload_and_resize_image(img):
    w, h = img.size
    if w/h > 2:
        img_src_list = [get_chopped_wide_img(img), img, img]
        target_size_list = resize_target_size['extreme']
        resize_edge = 'h'                   # resize base on short edge
        resize_edge_size_list = [_.size[1] for _ in img_src_list]
    elif h/w > 2:
        img_src_list = [get_chopped_high_img(img), img, img]
        target_size_list = resize_target_size['extreme']
        resize_edge = 'w'                   # resize base on short edge
        resize_edge_size_list = [_.size[0] for _ in img_src_list]
    else:
        img_src_list = [img, img, img]
        target_size_list = resize_target_size['normal']
        if w > h:                           # resize base on long edge
            resize_edge = 'w'
            resize_edge_size_list = [_.size[0] for _ in img_src_list]
        else:
            resize_edge = 'h'
            resize_edge_size_list = [_.size[1] for _ in img_src_list]


    flag_upload_list = [True,                                          # must upload thumb
                        resize_edge_size_list[1]>target_size_list[0],  # edge <= thumb target size, don't upload small
                        resize_edge_size_list[2]>target_size_list[1]]  # edge <= small target size, don't upload large

    flag_resize_list = [resize_edge_size_list[0]>target_size_list[0],
                        resize_edge_size_list[1]>target_size_list[1],
                        resize_edge_size_list[2]>target_size_list[2]]

    # UPLOAD
    res = {}
    _ = datetime.now()
    yy, mm = _.year, f"{_.month:0>2}"
    # g.uuid generated in post_image() view
    R2_BUCKET_NAME = current_app.config['R2_BUCKET_NAME']
    R2_CUSTOM_DOMAIN = current_app.config['R2_CUSTOM_DOMAIN']


    for (img_src, target_size, flag_upload, flag_resize, thumb_type) in zip(img_src_list,
                                                                            target_size_list,
                                                                            flag_upload_list,
                                                                            flag_resize_list,
                                                                            resize_target_type):
        if not flag_upload:
            continue
        if flag_resize:
            img_src = get_resized_img(img_src, resize_edge, target_size)

        # upload
        r2_key = f"{g.uid}/{yy}/{mm}/{g.image_uuid}_{thumb_type}.webp"
        buf = io.BytesIO()
        try:
            img_src.save(buf,
                         format="WEBP",
                         quality=75,
                         method=6,
                         optimize=True)
            buf.seek(0)

            current_app.r2_client.put_object(Bucket=R2_BUCKET_NAME,
                                             Key=r2_key,
                                             Body=buf,
                                             ContentType='image/webp')
            res.update({thumb_type: {'url': f"{R2_CUSTOM_DOMAIN}/{r2_key}",
                                     'width': img_src.size[0],
                                     'height': img_src.size[1],
                                     'size': buf.getbuffer().nbytes}})

        except Exception as e:
            res.update({'error': f"error occurred when uploading {thumb_type}: {e}"})
        finally:
            buf.close()

    return res
