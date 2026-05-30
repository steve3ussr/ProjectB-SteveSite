import steve_site
import pytest


def test_get_login_page(app, client):
    assert client.get('/auth/login').status_code == 200


@pytest.mark.skip
def test_db_data_import(app):
    with app.app_context():
        con = steve_site.db_api.db_open()
        res1 = con.execute("SELECT id, username, level FROM user").fetchall()
        res2 = con.execute("SELECT blog.id, user.username, blog.title, blog.status "
                           "FROM blog "
                           "LEFT JOIN user "
                           "ON blog.author_id = user.id").fetchall()


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

def test_register(): pass
def test_reset_password(): pass
def test_logout(): pass
