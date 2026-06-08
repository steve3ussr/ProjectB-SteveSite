import time, pytest
from steve_site.db_api import db_open, get_redis_client


@pytest.mark.parametrize(("username", "password", "uid"),
                         [('user1', 'password123user1', 1),
                          ('user1', 'password123user2', None),
                          ('operator1', 'password123operator1', 3),
                          ('admin1', 'password123admin1', 5)])
def test_login(app, username, password, uid):
    client = app.test_client()
    res = client.login(username, password)

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
def test_register(app, username, password, level):
    client = app.test_client()
    res = client.register(username, password, level)
    assert res.status_code == 200, res.json
    with client.session_transaction() as sess:
        assert sess.get('username', None) == username

    with app.app_context():
        con = db_open()
        curr_status = con.execute("SELECT * FROM user WHERE username=?", (username,)).fetchone()
        assert curr_status


def test_logout(app):
    client = app.test_client()
    client.login('user1', 'password123user1')
    res = client.logout()
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
def test_reset_password_normal(app, username, old_password, new_password, level):
    client = app.test_client()
    res = client.post_reset_pwd(username, level)
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
    res = client.post_new_pwd(new_password)
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
    client.logout()
    res = client.login(username, old_password)
    assert res.status_code == 400
    assert res.json.get('msg', None) == "用户名/密码错误"

    # check can log in with new pwd
    res = client.login(username, new_password)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


# @pytest.mark.skip(reason="耗时太长")
@pytest.mark.parametrize("wait_time", [70, 100])
@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_reset_password_timeout(app, username, old_password, new_password, level, wait_time):
    app.config['PERMANENT_SESSION_LIFETIME'] = 80
    client = app.test_client()
    res = client.post_reset_pwd(username, level)
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

    # check cannot set new-password
    time.sleep(wait_time)
    res = client.post_new_pwd(new_password)
    assert res.status_code == 400
    if wait_time > app.config['PERMANENT_SESSION_LIFETIME']:
        assert res.json['msg'] == 'Invalid session. '  # db not cleared, zombie entry
    else:
        assert res.json['msg'] == 'Token expired. 稍后自动跳转'
        client.get('/')
        with client.session_transaction() as sess:
            assert sess.get('reset_pwd_token', None) is None
        with app.app_context():
            con = db_open()
            res = con.execute("SELECT * FROM user_modify_tmp WHERE reset_pwd_token=?", (token,)).fetchone()
            assert res is None

    # check can log in with old pwd
    client.logout()
    res = client.login(username, old_password)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_reset_password_abort(app, username, old_password, new_password, level):
    client = app.test_client()
    res = client.post_reset_pwd(username, level)
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
    client.logout()
    res = client.login(username, old_password)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get('uid', None) is not None
        assert sess.get('username', None) is not None


def test_non_user_reset_password(app):
    client = app.test_client()
    res = client.post_new_pwd('pwd123')
    assert res.status_code == 400
    assert res.json.get('msg', None) == 'Invalid session. '


@pytest.mark.parametrize(("old_username", "password", "new_username", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_renew_username(app, old_username, password, new_username, level):
    # get uid
    with app.app_context():
        con = db_open()
        res = con.execute("SELECT * FROM user WHERE username=?", (old_username,)).fetchone()
        uid = res.get('id', None)
        assert uid is not None

    client = app.test_client()
    client.login(old_username, password)
    res = client.renew_usr(new_username)
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


def test_renew_username_guest(app):
    client = app.test_client()
    res = client.get('auth/renew-username')
    assert res.status_code == 302, res.json
    assert res.location == '/auth/login'


@pytest.mark.parametrize(("username", "old_password", "new_password", "level"),
                         [('user1', 'password123user1', 'pwd123', "User"),
                          ('operator1', 'password123operator1', 'pwd123', "Operator"),
                          ('admin1', 'password123admin1', 'pwd123', "Admin")])
def test_renew_password(app, username, old_password, new_password, level):
    # client log in, get uid
    client = app.test_client()
    client.login(username, old_password)
    with client.session_transaction() as sess:
        uid = sess.get('uid', None)
        assert uid is not None

    # renew password
    res = client.renew_pwd(new_password)
    assert res.status_code == 200, res.json
    assert res.json['redirect_url'] == '/'
    client.logout()
    client.get('/')

    # check client can log in with new password
    res = client.login(username, new_password)
    assert res.status_code == 200, res.json
    with client.session_transaction() as sess:
        assert sess.get('username', None) == username
        assert sess.get('uid', None) == uid

    # logout, check cannot log in with old password
    client.logout()
    client.get('/')
    res = client.login(username, old_password)
    assert res.status_code == 400
    assert res.json.get("msg", None) == "用户名/密码错误"


def test_renew_password_guest(app):
    client = app.test_client()
    res = client.get('auth/renew-password')
    assert res.status_code == 302
    assert res.location == '/auth/login'


@pytest.mark.parametrize("action", ["reset_pwd", "renew_usr", "renew_pwd"])
@pytest.mark.parametrize(("username", "password", "uid", "level"),
                         [('operator1', 'password123operator1', 3, "Operator")])
def test_force_logout_other_sessions(app, action, username, password, uid, level):
    with app.app_context():
        r = get_redis_client()
        assert not r.exists(f"user:sessions:{uid}")

        # client login
        clients = [app.test_client() for _ in range(5)]
        client1, client_others = clients[0], clients[1:]
        [c.login(username, password) for c in clients]

        # check session (5 remains)
        prev_session_list = r.smembers(f"user:sessions:{uid}")
        assert len(prev_session_list) == 5
        for sid in prev_session_list:
            assert r.exists(f"session:{sid.decode()}")
        for c in client_others:
            res = c.get('/auth/renew-username')
            assert res.status_code == 200, res.json

        # trigger force_logout
        if action == "reset_pwd":
            client1.reset_pwd(username, level, "any_valid_password")
        elif action == "renew_usr":
            client1.renew_usr("any_valid_username")
        elif action == "renew_pwd":
            client1.renew_pwd("any_valid_password")

        # check session (only 1 remain)
        curr_session_list = r.smembers(f"user:sessions:{uid}")
        assert len(curr_session_list) == 1
        for sid in prev_session_list:
            if sid in curr_session_list:
                assert r.exists(f"session:{sid.decode()}")
            else:
                assert not r.exists(f"session:{sid.decode()}")

        # check force re-login
        for c in client_others:
            res = c.get('/auth/renew-username')
            assert res.status_code == 302, res.json
            assert res.location == '/auth/login'


@pytest.mark.parametrize(("username", "password", "uid"),
                         [('operator1', 'password123operator1', 3)])
def test_clear_zombie_session(app, username, password, uid):
    app.config['PERMANENT_SESSION_LIFETIME'] = 60
    with app.app_context():
        r = get_redis_client()
        assert not r.exists(f"user:sessions:{uid}")

        # 5 clients login, redis session OK
        clients = [app.test_client() for _ in range(5)]
        [c.login(username, password) for c in clients]
        prev_session_list = r.smembers(f"user:sessions:{uid}")
        assert len(prev_session_list) == 5
        for sid in prev_session_list:
            assert r.exists(f"session:{sid.decode()}")

        # client1 keep renew session, others sleep
        client1, client_others = clients[0], clients[1:]
        for i in range(4):
            client1.get('/')
            time.sleep(20)

        # some session:{sid} auto expired
        curr_session_list = r.smembers(f"user:sessions:{uid}")
        assert len(curr_session_list) == 5
        cnt = 0
        for sid in curr_session_list:
            if r.exists(f"session:{sid.decode()}"):
                cnt += 1
        assert cnt == 1

        # trigger clear zombie session, check user:sessions:{uid} has only 1 active session
        client1.logout()
        client1.login(username, password)
        curr_session_list = r.smembers(f"user:sessions:{uid}")
        assert len(curr_session_list) == 1
        for c in client_others:
            res = c.get('/auth/renew-username')
            assert res.status_code == 302, res.json
            assert res.location == '/auth/login'
