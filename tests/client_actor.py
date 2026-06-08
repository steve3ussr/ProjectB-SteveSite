import os
import pyotp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask.testing import FlaskClient
from steve_site.db_api import db_open


load_dotenv()


def gen_reg_code(level):
    map_level = {'Admin': 'SECRET_OTP_ADMIN',
                 'Operator': 'SECRET_OTP_OPERATOR',
                 'User': 'SECRET_OTP_USER'}
    secret = os.getenv(map_level[level])
    assert secret is not None
    reg_code = pyotp.TOTP(secret).now()
    return reg_code


class ClientActor(FlaskClient):
    def login(self, usr, pwd):
        return self.post('/auth/login', json={'username': usr, 'password': pwd})

    def logout(self):
        return self.get('/auth/logout')

    def register(self, usr, pwd, level):
        return self.post('/auth/register', json={'username': usr,
                                                 'password': pwd,
                                                 'password-confirm': pwd,
                                                 'register-code': gen_reg_code(level)})

    def post_reset_pwd(self, usr, level):
        return self.post('/auth/reset-password', json={'username': usr,
                                                       'register-code': gen_reg_code(level)})

    def post_new_pwd(self, new_pwd):
        return self.post('/auth/new-password', json={'password': new_pwd,
                                                     'password-confirm': new_pwd})

    def reset_pwd(self, usr, level, new_pwd):
        res = self.post_reset_pwd(usr, level)
        assert res.status_code == 200, res.json
        assert res.json.get('redirect_url') == '/auth/new-password'
        return self.post_new_pwd(new_pwd)

    def renew_usr(self, new_usr):
        return self.post('/auth/renew-username', json={'username': new_usr})

    def renew_pwd(self, new_pwd):
        return self.post('/auth/renew-password', json={'password': new_pwd, 'password-confirm': new_pwd})

    def blog_view(self, bid, blog_info, expect_visibility):
        resp = self.get(f'/blog/{bid}')

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

        map_status = {"HIDDEN": "已隐藏: 非公开可见, 不可编辑",
                      "DRAFT": "草稿: 仅作者可见并编辑",
                      "DELETED": "已删除: 非公开可见, 可恢复",
                      "PENDING": "修改中: 非公开可见, 作者可编辑"}
        assert blog_info['status'] in map_status
        assert len(title_span_list) == 2
        assert title_span_list[1].text == map_status[blog_info['status']]

    def blog_delete(self, app,  bid, expect_res):
        resp = self.delete(f'/blog/{bid}/delete', follow_redirects=True)
        if expect_res:
            assert resp.status_code == 200
            with app.app_context():
                con = db_open()
                res = con.execute("SELECT * FROM blog WHERE id = ? AND status <> 'DELETED'", (bid,)).fetchone()
                assert res is None
        else:
            assert resp.status_code in (403, 409)

    def blog_publish(self, app, bid, expect_res):
        resp = self.post(f'/blog/{bid}/publish', follow_redirects=True)
        if expect_res:
            assert resp.status_code == 200
            with app.app_context():
                con = db_open()
                res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "PUBLIC"', (bid,)).fetchone()
                assert res is not None
        else:
            assert resp.status_code in (403, 409)

    def blog_submit(self, app, bid, expect_res):
        resp = self.post(f'/blog/{bid}/submit', follow_redirects=True)
        if expect_res:
            assert resp.status_code == 200
            with app.app_context():
                con = db_open()
                res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "HIDDEN"', (bid,)).fetchone()
                assert res is not None
        else:
            assert resp.status_code in (403, 409)

    def blog_hide(self, app, bid, expect_res):
        resp = self.post(f'/blog/{bid}/hide', follow_redirects=True)
        if expect_res:
            assert resp.status_code == 200
            with app.app_context():
                con = db_open()
                res = con.execute('SELECT * FROM blog WHERE id = ? AND status = "HIDDEN"', (bid,)).fetchone()
                assert res is not None
        else:
            assert resp.status_code in (403, 409)

    def blog_restore(self, app, bid, expect_res):
        with app.app_context():
            con = db_open()
            prev_status = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()['status']

        resp = self.post(f'/blog/{bid}/restore', follow_redirects=True)
        if expect_res:
            assert resp.status_code == 200
            with app.app_context():
                con = db_open()
                curr_status = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()['status']
                assert (prev_status, curr_status) in (('DELETED', 'PUBLIC'), ('HIDDEN', 'PENDING'))
        else:
            assert resp.status_code in (403, 409)

    def blog_edit_get(self, app, bid, expect_visibility):
        resp = self.get(f'/blog/{bid}/edit', follow_redirects=True)

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

    def blog_edit_publish(self, app, bid, expect_res):
        with app.app_context():
            con = db_open()
            _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
            prev_body = _['body']
            prev_title = _['title']

        resp = self.post(f"/blog/{bid}/edit",
                           follow_redirects=True,
                           json={'title': f"{prev_title}-modified",
                                 'content': f"modified-{prev_body}",
                                 'action': "publish"})
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

    def blog_edit_save(self, app, bid, expect_res):
        with app.app_context():
            con = db_open()
            _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
            prev_status = _['status']
            prev_body = _['body']
            prev_title = _['title']

        resp = self.post(f"/blog/{bid}/edit",
                           follow_redirects=True,
                           json={'title': f"{prev_title}-modified",
                                 'content': f"modified-{prev_body}",
                                 'action': "save"})
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

    def blog_edit_submit(self, app, bid, expect_res):
        with app.app_context():
            con = db_open()
            _ = con.execute('SELECT * FROM blog WHERE id = ?', (bid,)).fetchone()
            prev_body = _['body']
            prev_title = _['title']

        resp = self.post(f"/blog/{bid}/edit",
                           follow_redirects=True,
                           json={'title': f"{prev_title}-modified",
                                 'content': f"modified-{prev_body}",
                                 'action': "submit"})
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
