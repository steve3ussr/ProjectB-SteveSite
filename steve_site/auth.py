import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for
from steve_site.db_api import db_open


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=["GET", "POST"])
def login(msg=None):
    if request.method == 'GET':
        return render_template('login.html', msg=msg)

    usr, pwd = request.form['username-login'], request.form['password-login']
    con = db_open()
    res = con.execute("SELECT username, password FROM user WHERE username=?", (usr, )).fetchone()

    if res is None:
        return render_template('login.html', msg="用户名错误")

    if res[1] != pwd:
        return render_template('login.html', msg="密码错误")

    return "success"



