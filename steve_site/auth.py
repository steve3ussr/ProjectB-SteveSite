import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from steve_site.db_api import db_open
from functools import wraps


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.get('/login')
def login_get():
    return render_template('login.html')

@bp.post('/login')
def login_post():
    usr, pwd = request.form['username'], request.form['password']

    # verify username: length 3-30, a-zA-Z0-9_-@.
    if not re.match(r"[a-zA-Z0-9_\-@.]{3,30}", usr):
        flash("用户名要求: 长度3-30, 并且只包含英文、数字和特殊字符_-@.")
        return render_template('login.html')

    # verify password: length 6-30, a-zA-Z0-9_-@.
    if not re.match(r"[a-zA-Z0-9_\-@.]{6,30}", pwd):
        flash("密码要求: 长度6-30, 并且只包含英文、数字和特殊字符_-@.")
        return render_template('login.html', user_default=usr)

    con = db_open()
    res = con.execute("SELECT id, username, password FROM user WHERE username=?", (usr,)).fetchone()

    # case 1: new user, redirect to register
    if res is None:
        session['register-usr'] = usr
        session['register-pwd'] = pwd
        flash('看起来是位新用户！请输入邀请码')
        session['auth-register'] = True
        return redirect(url_for('auth.register'))

    # case 2: user exists
    if res['password'] != pwd:
        flash("密码错误")
        return render_template('login.html', user_default=usr)

    # case 3: correct usr+pwd, login success!
    session['uid'] = res['id']
    session['username'] = res['username']
    return redirect('/')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # abort any request except redirect from login
    auth_token = session.get('auth-register', None)
    if auth_token is None:
        abort(500)

    # GET
    if request.method == 'GET':
        return render_template('register.html', msg=None)

    # extract parameters for POST
    usr, pwd = session['register-usr'], session['register-pwd']
    reg_code = request.form['register-code']

    # error reg code
    if not (re.match(r"\d+", reg_code) and int(reg_code)%2027==0):
        flash('邀请码错误, 请重新输入')
        return render_template('register.html')

    # correct reg code
    ## stage 1: insert new user
    con = db_open()
    con.execute("INSERT INTO user(username, password) VALUES(?, ?)", (usr, pwd))
    con.commit()
    ## stage 2: get uid
    uid = con.execute("SELECT id FROM user WHERE username=?", (usr, )).fetchone()['id']
    session['uid'] = uid
    ## stage 3: delete outdate tokens
    session.pop('auth-register')
    session.pop('register-usr')
    session.pop('register-pwd')
    return redirect('/')

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
