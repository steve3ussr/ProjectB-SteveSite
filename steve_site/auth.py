import re
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify
from steve_site.db_api import db_open, get_redis_client
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import datetime, timedelta, timezone


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
    return render_template('auth/login.html')

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
    uid = res['id']
    session['uid'] = uid
    session['username'] = res['username']

    clear_zombie_session(uid)
    r = get_redis_client()
    if r and hasattr(session, 'sid'):
        r.sadd(f"user:sessions:{uid}", session.sid)

    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": "登录成功! 3s后跳转"}), 200  # TODO: add timeout, modify js


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # GET
    if request.method == 'GET':
        return render_template('auth/register.html', msg=None)

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
                      "RETURNING id", (usr, generate_password_hash(pwd), level))
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
    uid = session.get('uid')
    if uid:
        r = get_redis_client()
        if r and hasattr(session, 'sid'):
            r.srem(f"user:sessions:{uid}", session.sid)

    session.clear()  # or pop uid, username, history
    return redirect('/')

def force_login(f):
    @wraps(f)
    def _f(*args, **kwargs):
        if session.get('uid', None) is None:
            return redirect(url_for("auth.login_get"))
        return f(*args, **kwargs)
    return _f

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        return render_template('auth/reset-password.html')

    # extract parameters for POST
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    _ = [data.get(k, None) for k in ('username', 'register-code')]
    current_app.logger.info(f"register-post: {_}")
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400
    usr, reg_code = _

    # check user exists
    con = db_open()
    prev_info = con.execute("SELECT id, level FROM user WHERE username=?", (usr,)).fetchone()
    if prev_info is None:
        return jsonify({"status": "error", "msg": f"用户不存在"}), 400

    # verify reg_code
    curr_level = prev_info['level']
    next_level = current_app.otp_manager.verify(reg_code)
    if next_level is False or next_level != curr_level:
        return jsonify({"status": "error", "msg": "该验证码无效"}), 400

    # generate reset_pwd_token, reset_pwd_expire_time
    reset_pwd_token = secrets.token_urlsafe(32)
    reset_pwd_expire_time = datetime.now(timezone.utc) + timedelta(minutes=1)

    # add them to session and DB
    session['reset_pwd_token'] = reset_pwd_token
    res = con.execute("SELECT * FROM user_modify_tmp WHERE id=?", (prev_info['id'],)).fetchall()
    if not res:
        con.execute("INSERT INTO user_modify_tmp (id, reset_pwd_token, reset_pwd_expire_time) VALUES(?, ?, ?)",
                    (prev_info['id'], reset_pwd_token, reset_pwd_expire_time))
    else:
        con.execute("UPDATE user_modify_tmp SET reset_pwd_token=?, reset_pwd_expire_time=? WHERE id=?",
                    (reset_pwd_token, reset_pwd_expire_time, prev_info['id']))
    con.commit()

    return jsonify({"status": "success",
                    "redirect_url": url_for('auth.new_password'),
                    "msg": "重置成功! 即将自动登录并跳转"}), 200


@bp.route('/new-password', methods=['GET', 'POST'])
def new_password():
    if request.method == 'GET':
        return render_template('auth/new-password.html')

    # extract parameters for POST
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    _ = [data.get(k, None) for k in ('password', 'password-confirm')]
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400
    pwd, pwd_cfm = _

    # verify pwd == pwd_cfm
    if pwd != pwd_cfm:
        return jsonify({"status": "error", "msg": "Password disagree"}), 400

    # verify password format
    flag, reason = verify_password(pwd)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify session token, get username
    con = db_open()
    token = session.get('reset_pwd_token', '')
    user_tmp_info = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
    if token is None or user_tmp_info is None:
        return jsonify({"status": "error", "msg": "Invalid Token"}), 400

    # verify token expire
    exp_time = user_tmp_info.get('reset_pwd_expire_time', None)
    if exp_time is None:
        return jsonify({"status": "error", "msg": "Invalid Token"}), 400
    if datetime.now(timezone.utc) > exp_time:
        # clear session keys
        session.pop('reset_pwd_token', None)

        # clear db
        con.execute("DELETE FROM user_modify_tmp WHERE reset_pwd_token=?", (token,))
        con.commit()

        return jsonify({"status": "error",
                        "msg": "Token expired. 稍后自动跳转",
                        "redirect_url": url_for('auth.reset_password')}), 400

    # stage 1: modify user table
    cur = con.execute("UPDATE user SET password=? WHERE id=? RETURNING username",
                      (generate_password_hash(pwd), user_tmp_info.get('id'))
                      ).fetchone()
    username = cur['username']
    con.commit()

    # stage 2: clear db
    con.execute("DELETE FROM user_modify_tmp WHERE reset_pwd_token=?", (token,))
    con.commit()

    # stage 3: clear outdated session key
    session.pop('reset_pwd_token', None)

    # stage 4: set session keys
    session['uid'] = user_tmp_info.get('id')
    session['username'] = username
    force_logout_other_sessions(session['uid'], session.sid)
    current_app.logger.info(f"user register info: {session['uid']=}, {session['username']=}")
    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": ""}), 200


@bp.route('/renew-username', methods=['GET', 'POST'])
@force_login
def renew_username():
    if request.method == 'GET':
        return render_template('auth/renew-username.html')

    # extract parameters for POST
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    usr = data.get('username', None)
    if usr is None:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400

    # verify username format
    flag, reason = verify_username(usr)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify username is UNIQUE
    con = db_open()
    cur = con.execute("SELECT id FROM user WHERE username=?", (usr,)).fetchone()
    if cur is not None:
        return jsonify({"status": "warning", "msg": "该用户名已被占用"}), 400

    # verify uid
    uid = session.get('uid', None)
    if uid is None:
        return jsonify({"status": "error", "msg": "uid not exists"}), 400

    # change username
    con = db_open()
    con.execute("UPDATE user SET username=? WHERE id=?", (usr, uid))
    con.commit()
    session['username'] = usr
    force_logout_other_sessions(uid, session.sid)
    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": "修改成功! 即将自动登录并跳转"}), 200


@bp.route('/renew-password', methods=['GET', 'POST'])
@force_login
def renew_password():
    if request.method == 'GET':
        return render_template('auth/renew-password.html')

    # extract parameters for POST
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 400
    _ = [data.get(k, None) for k in ('password', 'password-confirm')]
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 400
    pwd, pwd_cfm = _

    # verify pwd == pwd_cfm
    if pwd != pwd_cfm:
        return jsonify({"status": "error", "msg": "Password disagree"}), 400

    # verify password format
    flag, reason = verify_password(pwd)
    if not flag:
        return jsonify({"status": "warning", "msg": reason}), 400

    # verify uid
    uid = session.get('uid', None)
    if uid is None:
        return jsonify({"status": "error", "msg": "uid not exists"}), 400

    # change password
    con = db_open()
    con.execute("UPDATE user SET password=? WHERE id=?", (generate_password_hash(pwd), uid))
    con.commit()
    force_logout_other_sessions(uid, session.sid)
    return jsonify({"status": "success",
                    "redirect_url": url_for('resp_index'),
                    "msg": "修改成功! 即将自动登录并跳转"}), 200

# TODO: user control panel: 只对admin开放，可以调整权限，查看统计

def clear_zombie_session(uid):  # triggered when login
    r = get_redis_client()
    if r is None:
        return

    user_session_map = f"user:sessions:{uid}"
    all_sids = r.smembers(user_session_map)

    for sid in all_sids:
        if not r.exists(f"session:{sid.decode()}"):
            r.srem(user_session_map, sid)


def force_logout_other_sessions(uid, curr_sid):  # triggered when renew-username/password, new-password
    r = get_redis_client()
    if r is None:
        return

    user_session_map = f"user:sessions:{uid}"
    all_sids = r.smembers(user_session_map)

    for sid in all_sids:
        if not r.exists(f"session:{sid.decode()}"):
            r.srem(user_session_map, sid)
        elif sid.decode() != curr_sid:
            r.srem(user_session_map, sid)
            r.unlink(f"session:{sid.decode()}")
