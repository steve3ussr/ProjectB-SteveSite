import re
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import steve_site
import pytest

from steve_site.db_api import db_open


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
    res = client.post('/auth/login',
                      content_type="application/x-www-form-urlencoded",
                      data=urlencode({'username': username, 'password': password}),
                      follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        if uid is not None:
            assert sess.get('uid', None) == uid
            assert sess.get('username', None) == username
        else:
            assert sess.get('username', None) is None
            assert sess.get('uid', None) is None


@pytest.fixture
def get_blog(blog_info):
    def _get_blog(uid, is_author, blog_status):
        for bid, info in blog_info.items():
            if is_author:
                if info['author_id'] == uid and info['status'] == blog_status:
                    return bid, info
            else:
                if info['author_id'] != uid and info['status'] == blog_status:
                    return bid, info
        raise SyntaxError
    return _get_blog


@pytest.fixture
def get_client(user_info, client_logged_in):
    def _get_client(user_level):
        for uid, info in user_info.items():
            if info['level'] != user_level:
                continue

            client = client_logged_in(info['username'], info['password'])
            return uid, info, client
        raise SyntaxError
    return _get_client


def action_view(client, bid, blog_info, expect_visibility):
    resp = client.get(f'/blog/{bid}')

    if not expect_visibility:
        assert resp.status_code == 404
        return

    # blog is visible
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    title_span_list = soup.select('h1.article-title > span')
    assert title_span_list[0].text == blog_info['title']

    if blog_info['status'] == 'PUBLIC':
        assert len(title_span_list) == 1
        return

    map_status = {"HIDDEN":  "已隐藏: 非公开可见, 不可编辑",
                  "DRAFT":   "草稿: 仅作者可见并编辑",
                  "DELETED": "已删除: 非公开可见, 可恢复",
                  "PENDING": "修改中: 非公开可见, 作者可编辑"}
    assert blog_info['status'] in map_status
    assert len(title_span_list) == 2
    assert title_span_list[1].text == map_status[blog_info['status']]


def action_delete(app, client, bid, expect_res):
    resp = client.delete(f'/blog/{bid}/delete', follow_redirects=True)
    if expect_res:
        assert resp.status_code == 200
        with app.app_context():
            con = db_open()
            res = con.execute("SELECT * FROM blog WHERE id = ? AND status <> 'DELETED'", (bid,)).fetchone()
            assert res is None
    else:
        assert resp.status_code in (403, 409)


def action_publish(app, client, bid, expect_res):
    resp = client.post(f'/blog/{bid}/publish', follow_redirects=True)
    if expect_res:
        assert resp.status_code == 200
        with app.app_context():
            con = db_open()
            res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "PUBLIC"', (bid,)).fetchone()
            assert res is not None
    else:
        assert resp.status_code in (403, 409)


def action_submit(app, client, bid, expect_res):
    resp = client.post(f'/blog/{bid}/submit', follow_redirects=True)
    if expect_res:
        assert resp.status_code == 200
        with app.app_context():
            con = db_open()
            res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "HIDDEN"', (bid,)).fetchone()
            assert res is not None
    else:
        assert resp.status_code in (403, 409)


def action_hide(app, client, bid, expect_res):
    resp = client.post(f'/blog/{bid}/hide', follow_redirects=True)
    if expect_res:
        assert resp.status_code == 200
        with app.app_context():
            con = db_open()
            res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "HIDDEN"', (bid,)).fetchone()
            assert res is not None
    else:
        assert resp.status_code in (403, 409)


def action_restore(app, client, bid, expect_res):
    with app.app_context():
        con = db_open()
        prev_status = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()['status']

    resp = client.post(f'/blog/{bid}/restore', follow_redirects=True)
    if expect_res:
        assert resp.status_code == 200
        with app.app_context():
            con = db_open()
            curr_status = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()['status']
            assert (prev_status, curr_status) in (('DELETED', 'PUBLIC'), ('HIDDEN', 'PENDING'))
    else:
        assert resp.status_code in (403, 409)


def action_edit_get(app, client, bid, expect_visibility):
    resp = client.get(f'/blog/{bid}/edit', follow_redirects=True)

    if not expect_visibility:
        assert resp.status_code in (403, 409)
        return

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, 'html.parser')

    mde_container = soup.select("div.EasyMDEContainer")
    assert len(mde_container) != 1

    action_btn_text_set = set([btn.get('value', None) for btn in soup.select("button[type='submit']")])

    with app.app_context():
        con = db_open()
        curr_status = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()['status']
    if curr_status == 'PUBLIC':
        assert action_btn_text_set == {"publish"}
    elif curr_status == 'DRAFT':
        assert action_btn_text_set == {"publish", "save"}
    elif curr_status == 'PENDING':
        assert action_btn_text_set == {"submit", "save"}
    else:
        assert action_btn_text_set == set()


def action_edit_publish(app, client, bid, expect_res):
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        prev_status = _['status']
        prev_body = _['body']
        prev_title = _['title']

    resp = client.post(f"/blog/{bid}/edit",
                       follow_redirects=True,
                       content_type='application/x-www-form-urlencoded',
                       data = urlencode({'title': f"{prev_title}-modified",
                                         'content': f"modified-{prev_body}",
                                         'action': "publish"}))
    if not expect_res:
        assert resp.status_code in (403, 409)
        return

    assert resp.status_code == 200
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        curr_status = _['status']
        curr_body = _['body']
        curr_title = _['title']
        assert curr_status == 'PUBLIC' and curr_body == f"modified-{prev_body}" and curr_title == f"{prev_title}-modified"


def action_edit_save(app, client, bid, expect_res):
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        prev_status = _['status']
        prev_body = _['body']
        prev_title = _['title']

    resp = client.post(f"/blog/{bid}/edit",
                       follow_redirects=True,
                       content_type='application/x-www-form-urlencoded',
                       data=urlencode({'title': f"{prev_title}-modified",
                                       'content': f"modified-{prev_body}",
                                       'action': "save"}))
    if not expect_res:
        assert resp.status_code in (403, 409)
        return

    assert resp.status_code == 200
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        curr_status = _['status']
        curr_body = _['body']
        curr_title = _['title']
        assert curr_status == prev_status and curr_body == f"modified-{prev_body}" and curr_title == f"{prev_title}-modified"


def action_edit_submit(app, client, bid, expect_res):
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        prev_status = _['status']
        prev_body = _['body']
        prev_title = _['title']

    resp = client.post(f"/blog/{bid}/edit",
                       follow_redirects=True,
                       content_type='application/x-www-form-urlencoded',
                       data=urlencode({'title': f"{prev_title}-modified",
                                       'content': f"modified-{prev_body}",
                                       'action': "submit"}))
    if not expect_res:
        assert resp.status_code in (403, 409)
        return

    assert resp.status_code == 200
    with app.app_context():
        con = db_open()
        _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
        curr_status = _['status']
        curr_body = _['body']
        curr_title = _['title']
        assert curr_status == "HIDDEN" and curr_body == f"modified-{prev_body}" and curr_title == f"{prev_title}-modified"


def get_test_res(user_level, is_author, blog_status, action):
    map_res = {
        "User": {
            True: {
                "PUBLIC":   (1,1,0,0,0,0,1,1,0,0),
                'DRAFT':    (1,1,1,0,0,0,1,1,1,0),
                "PENDING":  (1,1,0,1,0,0,1,0,1,1),
                "HIDDEN":   (1,1,0,0,0,0,0,0,0,0),
                "DELETED":  (0,0,0,0,0,0,0,0,0,0),
            },
            False: {
                "PUBLIC":   (1,0,0,0,0,0,0,0,0,0),
                'DRAFT':    (0,0,0,0,0,0,0,0,0,0),
                "PENDING":  (0,0,0,0,0,0,0,0,0,0),
                "HIDDEN":   (0,0,0,0,0,0,0,0,0,0),
                "DELETED":  (0,0,0,0,0,0,0,0,0,0),
            }
        },
        "Operator": {
            True: {
                "PUBLIC":   (1,1,0,0,1,0,1,1,0,0),
                'DRAFT':    (1,1,1,0,0,0,1,1,1,0),
                "PENDING":  (1,1,0,1,0,0,1,0,1,1),
                "HIDDEN":   (1,1,1,0,0,0,0,0,0,0),
                "DELETED":  (0,0,0,0,0,0,0,0,0,0),
            },
            False: {
                "PUBLIC":   (1,0,0,0,1,0,0,0,0,0),
                'DRAFT':    (0,0,0,0,0,0,0,0,0,0),
                "PENDING":  (0,0,0,0,0,0,0,0,0,0),
                "HIDDEN":   (1,0,1,0,0,0,0,0,0,0),
                "DELETED":  (0,0,0,0,0,0,0,0,0,0),
            }
        },
        "Admin": {
            True: {
                "PUBLIC":   (1,1,0,0,1,0,1,1,0,0),
                'DRAFT':    (1,1,1,0,0,0,1,1,1,0),
                "PENDING":  (1,1,0,1,0,0,1,0,1,1),
                "HIDDEN":   (1,1,1,0,0,1,0,0,0,0),
                "DELETED":  (1,0,0,0,0,1,0,0,0,0),
            },
            False: {
                "PUBLIC":   (1,0,0,0,1,0,0,0,0,0),
                'DRAFT':    (0,0,0,0,0,0,0,0,0,0),
                "PENDING":  (1,0,0,0,0,0,0,0,0,0),
                "HIDDEN":   (1,0,1,0,0,1,0,0,0,0),
                "DELETED":  (1,0,0,0,0,1,0,0,0,0),
            }
        }
    }

    res_array = map_res[user_level][is_author][blog_status]
    i = ['view', 'delete', 'publish', 'submit', 'hide', 'restore',
                                    'edit-get', 'edit-publish', 'edit-save', 'edit-submit'].index(action)
    return res_array[i]


@pytest.mark.parametrize('action', ['view', 'delete', 'publish', 'submit', 'hide', 'restore',
                                    'edit-get', 'edit-publish', 'edit-save', 'edit-submit'])
@pytest.mark.parametrize('blog_status', ['PENDING', "HIDDEN", "DRAFT", "DELETED", "PUBLIC"])
@pytest.mark.parametrize('is_author', [True, False])
@pytest.mark.parametrize('user_level', ["User", "Operator", "Admin"])
def test_blog_status_trans(app, get_client, get_blog, user_level, is_author, blog_status, action):
    uid, user_info, client = get_client(user_level)
    bid, blog_info = get_blog(uid, is_author, blog_status)
    expect_res = get_test_res(user_level, is_author, blog_status, action)

    if action == 'view':
        action_view(client, bid, blog_info, expect_res)
    elif action == 'delete':
        action_delete(app, client, bid, expect_res)
    elif action == 'publish':
        action_publish(app, client, bid, expect_res)
    elif action == 'submit':
        action_submit(app, client, bid, expect_res)
    elif action == 'hide':
        action_hide(app, client, bid, expect_res)
    elif action == 'restore':
        action_restore(app, client, bid, expect_res)
    elif action == 'edit-get':
        action_edit_get(app, client, bid, expect_res)
    elif action == 'edit-publish':
        action_edit_publish(app, client, bid, expect_res)
    elif action == 'edit-save':
        action_edit_save(app, client, bid, expect_res)
    elif action == 'edit-submit':
        action_edit_submit(app, client, bid, expect_res)
