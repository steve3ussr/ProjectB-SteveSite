from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort

from steve_site.auth import force_login
from steve_site.db_api import db_open


bp = Blueprint('blog', __name__, url_prefix='/blog')


def shorten_between(s, limit):
    if len(s) <= limit:
        return s

    limit = (limit-4)//2
    return f"{s[:limit]}...{s[-limit:]}"

def shorten_start(s, limit):
    if len(s) <= limit:
        return s
    return s[:limit]

def time_decide(s1, s2, delimiter='.'):
    t1 = datetime.fromisoformat(s1)
    t2 = datetime.fromisoformat(s2)
    res = t1 if t1 >= t2 else t2
    return res.strftime('%Y.%m.%d')


@bp.route('/', methods=['GET'])
def index_get():
    con = db_open()
    res = con.execute('SELECT blog.id AS blog_id, user.username AS author, blog.title AS title, blog.body AS body, blog.created AS time_create, blog.edited AS time_edit FROM blog LEFT JOIN user ON blog.author_id = user.id').fetchall()

    blogs = []
    for row in res:
        _blogs = {'href_link': f"/blog/{row['blog_id']}",
                  'author': row['author'],
                  'title': shorten_between(row['title'], 20),
                  'body': shorten_start(row['body'], 80),
                  'time_dot': time_decide(row['time_create'], row['time_edit']),
                  'time_dash': time_decide(row['time_create'], row['time_edit'], '-')}
        blogs.append(_blogs)

    # blogs is a list of dict
    return render_template('blog.html', blog_entry_list=blogs)

@bp.route('/', methods=['POST'])
def index_post():
    return render_template('blog.html')

@bp.route('/add', methods=['GET'])
@force_login
def blog_add_get():
    return render_template('blog_editor.html')

@bp.route('/add', methods=['POST'])
@force_login
def blog_add_post():
    title = request.form['title']
    content = request.form['content']
    uid = session.get('uid')

    con = db_open()
    cur = con.execute("INSERT INTO blog (author_id, title, body) VALUES (?, ?, ?) RETURNING id", (uid, title, content))

    blog_id = cur.fetchone()['id']
    con.commit()
    return redirect(f'/blog/{blog_id}')

@bp.route('/edit/<int:bid>')
@force_login
def blog_edit(bid):
    return render_template('blog_editor.html')

@bp.route('/delete/<int:bid>')
@force_login
def blog_delete(bid):
    con = db_open()
    cur = con.execute("DELETE FROM blog WHERE id = ?", (bid,))
    con.commit()
    return redirect(url_for('blog.index_get'))

@bp.route('/<int:bid>')
def blog_view(bid):
    con = db_open()
    blog_detail = con.execute("SELECT * FROM blog WHERE id = ?", (bid, )).fetchone()



    return render_template('blog_detail.html', blog_entry=blog_detail)

@bp.route('/test_view')
def blog_test():
    return render_template('blog_detail.html')

@bp.route('/test_edit')
def blog_edit_test():
    return render_template('blog_editor.html')