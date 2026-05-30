import os
import tempfile
from urllib.parse import urlencode
import pytest
import steve_site
from steve_site.db_api import db_open
from werkzeug.security import generate_password_hash


@pytest.fixture
def user_info():
    user_list = [("user1", "password123user1", "User"),
                 ("user2", "password123user2", "User"),
                 ("operator1", "password123operator1", "Operator"),
                 ("operator2", "password123operator2", "Operator"),
                 ("admin1", "password123admin1", "Admin"),
                 ("admin2", "password123admin2", "Admin")]
    res = {}
    for uid, (username, password, level) in enumerate(user_list, 1):
        res[uid] = {'username': username, "password": password, "level": level}
    return res


@pytest.fixture
def blog_info():
    blog_list = [(1, "User-PUBLIC", "", "PUBLIC"),
                 (1, "User-DRAFT", "", "DRAFT"),
                 (1, "User-PENDING", "", "PENDING"),
                 (1, "User-HIDDEN", "", "HIDDEN"),
                 (1, "User-DELETED", "", "DELETED"),
                 (3, "Operator-PUBLIC", "", "PUBLIC"),
                 (3, "Operator-DRAFT", "", "DRAFT"),
                 (3, "Operator-PENDING", "", "PENDING"),
                 (3, "Operator-HIDDEN", "", "HIDDEN"),
                 (3, "Operator-DELETED", "", "DELETED"),
                 (5, "Admin-PUBLIC", "", "PUBLIC"),
                 (5, "Admin-DRAFT", "", "DRAFT"),
                 (5, "Admin-PENDING", "", "PENDING"),
                 (5, "Admin-HIDDEN", "", "HIDDEN"),
                 (5, "Admin-DELETED", "", "DELETED")]
    res = {}
    for bid, (author_id, title, body, status) in enumerate(blog_list, 1):
        res[bid] = {'author_id': author_id, "title": title, "body": body, "status": status}
    return res


@pytest.fixture
def app(user_info, blog_info):
    db_fd, db_path = tempfile.mkstemp()
    app = steve_site.create_app(test_config={'DB': db_path,
                                             'SECRET_KEY': os.urandom(24),
                                             'TEST_FORCE_CREATE_DB': True})

    with app.app_context():
        con = db_open()
        lst = [(info['username'],
                generate_password_hash(info['password']),
                info['level']) for info in user_info.values()]
        con.executemany("INSERT INTO user (username, password, level) VALUES (?, ?, ?)", lst)

        lst = [(info['author_id'],
                info['title'],
                info['body'],
                info['status']) for info in blog_info.values()]
        con.executemany("INSERT INTO blog (author_id, title, body, status) VALUES (?, ?, ?, ?)", lst)
        con.commit()
    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def client_logged_in(client):
    def _client_logged_in(username, password):
        res = client.post('/auth/login',
                          json={'username': username, 'password': password})
        assert res.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('username', None) == username
        return client
    return _client_logged_in
