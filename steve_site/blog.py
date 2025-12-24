from datetime import datetime
from importlib.resources import contents

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, current_app, g

from steve_site.auth import force_login
from steve_site.db_api import db_open


bp = Blueprint('blog', __name__, url_prefix='/blog')


def shorten_blog_title(s, limit):
    if len(s) <= limit:
        return s
    limit = (limit-4)//2
    return f"{s[:limit]}...{s[-limit:]}"

def shorten_blog_body(s, limit=70):
    if len(s) <= limit:
        return s
    return s[:limit] + '...[点击查看全文]'

def time_decide(s1, s2, delimiter='.'):
    t1 = datetime.fromisoformat(s1)
    t2 = datetime.fromisoformat(s2)
    res = t1 if t1 >= t2 else t2
    return res.strftime(f'%Y{delimiter}%m{delimiter}%d-%H:%M:%S')

@bp.route('/', methods=['GET', 'POST'])
def index():
    con = db_open()
    res = con.execute('SELECT blog.id AS blog_id, '
                      'user.username AS author, '
                      'blog.title AS title, '
                      'blog.body AS body, '
                      'blog.created AS time_create, '
                      'blog.edited AS time_edit, '
                      'blog.deleted_at AS time_delete '
                      'FROM blog LEFT JOIN user '
                      'ON blog.author_id = user.id').fetchall()

    # deleted blogs are excluded
    blogs = []
    for row in res:
        if row['time_delete'] is not None:
            continue
        _blogs = {'id': row['blog_id'],
                  'author': row['author'],
                  'title': shorten_blog_title(row['title'], 20),
                  'body': shorten_blog_body(row['body']),
                  'time_dot': time_decide(row['time_create'], row['time_edit']),
                  'time_dash': time_decide(row['time_create'], row['time_edit'], '-')}
        blogs.append(_blogs)

    # GET method: return blog list
    if request.method == 'GET':
        return render_template('blog.html', blog_entry_list=blogs)
    # TODO: POST method is not implemented
    return render_template('blog.html', blog_entry_list=blogs)

@bp.route('/add', methods=["GET", "POST"])
@force_login
def add():
    # GET method
    if request.method == 'GET':
        return render_template('blog_editor.html')

    # POST method
    title = request.form['title']
    content = request.form['content']
    uid = session.get('uid')

    con = db_open()
    cur = con.execute("INSERT INTO blog (author_id, title, body) "
                      "VALUES (?, ?, ?) "
                      "RETURNING id",
                      (uid, title, content))
    blog_id = cur.fetchone()['id']
    con.commit()
    return redirect(url_for('blog.view', bid=blog_id))

@bp.get('/<int:bid>')
def view(bid):
    con = db_open()
    blog_detail = con.execute("SELECT * FROM blog WHERE id = ?", (bid, )).fetchone()
    if not blog_detail:
        abort(404)
    return render_template('blog_detail.html', blog_entry=blog_detail)

@bp.route('/<int:bid>/delete', methods=['DELETE'])
@force_login
def delete(bid):
    error_code, desc, status_code = _authenticated_and_authorize(bid)
    if error_code:
        current_app.logger.error(f"[blog-delete]: {error_code=}, {desc=}")
        return redirect(url_for(f"status_page_{status_code}"), code=303)

    g.con = db_open()
    g.con.execute("UPDATE blog SET deleted_at=CURRENT_TIMESTAMP WHERE id = ?", (bid,))
    g.con.commit()
    return redirect(url_for('blog.index'), code=303)

@bp.route('/<int:bid>/edit', methods=["GET", "POST"])
@force_login
def edit(bid):
    error_code, desc, status_code = _authenticated_and_authorize(bid)
    if error_code:
        current_app.logger.error(f"[blog-delete]: {error_code=}, {desc=}")
        return redirect(url_for(f"status_page_{status_code}"), code=303)

    g.con = db_open()

    # GET method
    if request.method == 'GET':
        data = g.con.execute("SELECT title, body FROM blog WHERE id = ?", (bid,)).fetchone()
        return render_template('blog_editor.html',
                               blog_detail=data,
                               submit_href=url_for("blog.edit", bid=bid))

    # POST method
    title = request.form['title']
    content = request.form['content']
    g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP WHERE id=?", (title, content, bid))
    g.con.commit()
    return redirect(url_for('blog.view', bid=bid))

def _authenticated_and_authorize(bid):
    """
    check edit/delete has Auth and Auth
    :return: tuple like (error code, description, HTTP status code)
    """
    # query blog author
    g.con = db_open()
    cur = g.con.execute("SELECT author_id FROM blog WHERE id=?", (bid,)).fetchone()

    # error code 20002: blog id non-exists
    if not cur:
        return 20002, 'non-exist blog id', 404

    # error code 20001: not login, which will logged as ERROR because this SHOULD DEFINITELY NOT HAPPEN
    uid = session.get('uid', None)
    if uid is None:
        current_app.logger.error(f"[blog-authenticate-and-authorize]: user not logged in")
        return 20001, 'no user login info', 401

    # error code 20003: blog author != current user, unauthorized
    if cur['author_id'] != uid:
        return 20003, 'unauthorized, user is not blog author', 403

    return 0, 'auth and auth', 200
