import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, current_app, jsonify
from steve_site.db_api import db_open
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


bp = Blueprint('auth', __name__, url_prefix='/auth')


def verify_username(s):
    if not re.match(r"[a-zA-Z0-9_\-@.]{3,30}", s):
        return False, "用户名要求: 长度3-30, 并且只包含英文、数字和特殊字符_-@."
    else:
        return True, ""


def verify_password(s):
    if not re.match(r"[a-zA-Z0-9_\-@.]{6,30}", s):
        return False, "密码要求: 长度6-30, 并且只包含英文、数字和特殊字符_-@."
    else:
        return True, ""


@bp.get('/login')
def login_get():
    return render_template('login.html')

@bp.post('/login')
def login_post():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    _ = [data.get(k, None) for k in ('username', 'password')]
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400
    usr, pwd = _

    # verify username
    flag, reason = verify_username(usr)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify password: length 6-30, a-zA-Z0-9_-@.
    flag, reason = verify_password(pwd)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    con = db_open()
    res = con.execute("SELECT id, username, password FROM user WHERE username=?", (usr,)).fetchone()

    # case 1: user not exists
    if res is None:
        return jsonify({"status": "error",
                        "msg": "用户名/密码错误"}), 400

    # case 2: user exists, but wrong password
    if not check_password_hash(res['password'], pwd):
        return jsonify({"status": "error",
                        "msg": "用户名/密码错误"}), 400

    # case 3: correct usr+pwd, login success!
    session['uid'] = res['id']
    session['username'] = res['username']
    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": ""}), 200


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # GET
    if request.method == 'GET':
        return render_template('register.html', msg=None)

    # extract parameters for POST
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    _ = [data.get(k, None) for k in ('username', 'password', 'password-confirm', 'register-code')]
    current_app.logger.info(f"register-post: {_}")
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400
    usr, pwd, pwd_cfm, reg_code = _

    # verify pwd == pwd_cfm
    if pwd != pwd_cfm:
        return jsonify({"status": "error", "msg": "Password disagree"}), 400

    # verify username format
    flag, reason = verify_username(usr)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify password format
    flag, reason = verify_password(pwd)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify username is UNIQUE
    con = db_open()
    cur = con.execute("SELECT id FROM user WHERE username=?", (usr,)).fetchone()
    if cur is not None:
        return jsonify({"status": "warning", "msg": "该用户名已被占用"}), 400

    # verify reg code
    level = current_app.otp_manager.verify(reg_code)
    if level is False:
        return jsonify({"status": "error", "msg": "该邀请码不可用"}), 400


    # stage1: insert username
    cur = con.execute("INSERT INTO user(username, password, level) "
                      "VALUES(?, ?, ?)"
                      "RETURNING id", (usr, pwd, level))
    uid = cur.fetchone()['id']
    con.commit()

    ## stage 2: set session tokens
    session['uid'] = uid
    session['username'] = usr
    current_app.logger.info(f"user register info: {usr=}, {uid=}, {level=}")
    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": ""}), 200

@bp.route('/logout')
def logout():
    pop_key_list = ['uid', 'username', 'history']
    for key in pop_key_list:
        _ = session.pop(key, None)
    return redirect('/')

def force_login(f):
    @wraps(f)
    def _f(*args, **kwargs):
        if session.get('uid', None) is None:
            return redirect(url_for("auth.login_get"))
        return f(*args, **kwargs)
    return _f
