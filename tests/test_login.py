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
