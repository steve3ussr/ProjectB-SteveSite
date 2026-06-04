import os, time, pytest, pyotp
from dotenv import load_dotenv
from steve_site.db_api import db_open


def gen_reg_code(level):
    load_dotenv()
    map_level = {'Admin': 'SECRET_OTP_ADMIN',
                 'Operator': 'SECRET_OTP_OPERATOR',
                 'User': 'SECRET_OTP_USER'}
    secret = os.getenv(map_level[level])
    assert secret is not None
    time.sleep(3)
    reg_code = pyotp.TOTP(secret).now()
    return reg_code


@pytest.mark.parametrize(("username", "password", "uid"),
                         [('user1', 'password123user1', 1),
                          ('user1', 'password123user2', None),
                          ('operator1', 'password123operator1', 3),
                          ('admin1', 'password123admin1', 5)])
def test_login(app, client, username, password, uid):
    res = client.post('/auth/login', json={'username': username, 'password': password})

    if uid is None:
        assert res.status_code == 400
        assert res.json.get("msg", None) == "用户名/密码错误"
        return

    assert res.status_code == 200
    with client.session_transaction() as sess:
        if uid is not None:
            assert sess.get('uid', None) == uid
            assert sess.get('username', None) == username
        else:
            assert sess.get('username', None) is None
            assert sess.get('uid', None) is None


@pytest.mark.parametrize('level', ['Admin', 'Operator', 'User'])
@pytest.mark.parametrize(("username", "password"),
                         [('new-user', 'password123')])
def test_register(app, client, username, password, level):
    res = client.post('/auth/register', json={'username': username,
                                              'password': password,
                                              'password-confirm': password,
                                              'register-code': gen_reg_code(level)})
    assert res.status_code == 200, res.json
    with client.session_transaction() as sess:
        assert sess.get('username', None) == username

    with app.app_context():
        con = db_open()
        curr_status = con.execute("SELECT * FROM user WHERE username=?", (username,)).fetchone()
        assert curr_status


def test_logout(app, client_logged_in):
    client = client_logged_in('user1', 'password123user1')
    res = client.get('/auth/logout')
    assert res.status_code == 302
    assert res.location == '/'
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is None
        assert sess.get('username', None) is None
        assert sess.get('history', None) is None


@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_reset_password_normal(app, client, username, old_password, new_password, level):
    res = client.post('/auth/reset-password', json={'username': username,
                                                    'register-code': gen_reg_code(level)})
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/auth/new-password'
    client.get('/auth/new-password')

    # check session push token
    with client.session_transaction() as sess:
        token = sess.get('reset_pwd_token', None)
        assert token is not None

    # check db UPDATE expire time
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
        assert res
        exp_time = res['reset_pwd_expire_time']
        assert exp_time

    # check can set new-password
    res = client.post('/auth/new-password', json={'password': new_password, 'password-confirm': new_password})
    assert res.status_code == 200
    assert res.json['redirect_url'] == '/'
    client.get('/')
    with client.session_transaction() as sess:
        assert sess.get('reset_pwd_token', None) is None
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
        assert res is None

    # check cannot log in with old pwd
    client.get('/auth/logout')
    res = client.post('/auth/login', json={'username': username, 'password': old_password})
    assert res.status_code == 400
    assert res.json.get('msg', None) == "用户名/密码错误"

    # check can log in with new pwd
    res = client.post('auth/login', json={'username': username, 'password': new_password})
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


# @pytest.mark.skip(reason="耗时太长")
@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_reset_password_timeout(app, client, username, old_password, new_password, level):
    res = client.post('/auth/reset-password', json={'username': username,
                                                    'register-code': gen_reg_code(level)})
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/auth/new-password'
    client.get('/auth/new-password')

    # check session push token
    with client.session_transaction() as sess:
        token = sess.get('reset_pwd_token', None)
        assert token is not None

    # check db UPDATE expire time
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
        assert res
        exp_time = res['reset_pwd_expire_time']
        assert exp_time

    # check can set new-password
    time.sleep(310)
    res = client.post('/auth/new-password', json={'password': new_password, 'password-confirm': new_password})
    assert res.status_code == 400
    assert res.json['msg'] == 'Token expired. 稍后自动跳转'
    client.get('/')
    with client.session_transaction() as sess:
        assert sess.get('reset_pwd_token', None) is None
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
        assert res is None

    # check can log in with old pwd
    client.get('/auth/logout')
    res = client.post('/auth/login', json={'username': username, 'password': old_password})
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_reset_password_abort(app, client, username, old_password, new_password, level):
    res = client.post('/auth/reset-password', json={'username': username,
                                                    'register-code': gen_reg_code(level)})
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/auth/new-password'
    client.get('/auth/new-password')

    # check session push token
    with client.session_transaction() as sess:
        token = sess.get('reset_pwd_token', None)
        assert token is not None

    # check db UPDATE expire time
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
        assert res
        exp_time = res['reset_pwd_expire_time']
        assert exp_time

    # check can log in with old pwd
    client.get('/auth/logout')
    res = client.post('/auth/login', json={'username': username, 'password': old_password})
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


def test_non_user_reset_password(app, client):
    res = client.post('/auth/new-password', json={'password': 'pwd123', 'password-confirm': 'pwd123'})
    assert res.status_code == 400
    assert res.json.get('msg', None) == 'Invalid Token'


@pytest.mark.parametrize(("old_username", "password", "new_username", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_renew_username(app, client_logged_in, old_username, password, new_username, level):
    # get uid
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user WHERE username=?", (old_username,)).fetchone()
        uid = res.get('id', None)
        assert uid is not None

    client = client_logged_in(old_username, password)
    res = client.post('/auth/renew-username', json={'username': new_username})
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/'
    client.get('/auth/new-password')

    # verify username is changed
    client.get('/')
    with client.session_transaction() as sess:
        assert sess.get('username', None) == new_username
        assert sess.get('uid', None) == uid

    # check db
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user WHERE id=?", (uid,)).fetchone()
        assert res['username'] == new_username


def test_renew_username_guest(app, client):
    res = client.get('auth/renew-username')
    assert res.status_code == 302, res.json
    assert res.location == '/auth/login'


@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_renew_password(app, client_logged_in, username, old_password, new_password, level):
    # client log in, get uid
    client = client_logged_in(username, old_password)
    with client.session_transaction() as sess:
        uid = sess.get('uid', None)
        assert uid is not None

    # renew password
    res = client.post('/auth/renew-password', json={'password': new_password, 'password-confirm': new_password})
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/'
    client.get('/auth/logout')
    client.get('/')

    # check client can log in with new password
    res = client.post('/auth/login', json={'username': username, 'password': new_password})
    assert res.status_code == 200, res.json
    with client.session_transaction() as sess:
        assert sess.get('username', None) == username
        assert sess.get('uid', None) == uid

    # logout, check cannot log in with old password
    client.get('/auth/logout')
    client.get('/')
    res = client.post('/auth/login', json={'username': username, 'password': old_password})
    assert res.status_code == 400
    assert res.json.get("msg", None) == "用户名/密码错误"


def test_renew_password_guest(app, client):
    res = client.get('auth/renew-password')
    assert res.status_code == 302
    assert res.location == '/auth/login'
