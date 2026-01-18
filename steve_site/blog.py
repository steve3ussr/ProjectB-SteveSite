from flask import Blueprint, render_template, request, redirect, url_for, session, abort, current_app, g
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


def time_decide(t1, t2, fmt=f'%Y-%m-%d %H:%M:%S'):
    res = t1 if t1 >= t2 else t2
    return res.strftime(fmt)


@bp.get('/')
def index():
    # parse GET request args if possible
    sort_type = request.args.get('sort', None)
    search_keyword = request.args.get('keyword', None)
    flag_mine_only = request.args.get('my_posts') == 'on'
    sidebar_default_value = {'sort_type': sort_type,
                             'search_keyword': search_keyword,
                             'flag_mine_only': flag_mine_only}

    # SEARCH_KEYWORD
    if search_keyword is None or search_keyword.strip() == '':
        sql_search = ""
    else:
        sql_search = (f"WHERE title LIKE '%{search_keyword}%' OR"
                      f"body LIKE '%{search_keyword}%'")

    # GET BLOG LIST
    g.con = db_open()
    res = g.con.execute('SELECT blog.id AS blog_id, '
                      'user.username AS author, '
                      'blog.title AS title, '
                      'blog.body AS body, '
                      'blog.created AS time_create, '
                      'blog.edited AS time_edit, '
                      'blog.deleted_at AS time_delete, '
                      'blog.pv AS pv '
                      'FROM blog LEFT JOIN user '
                      'ON blog.author_id = user.id').fetchall()
    blogs = []
    for row in res:
        if row['time_delete'] is not None:
            continue
        _blogs = {'id': row['blog_id'],
                  'author': row['author'],
                  'title': shorten_blog_title(row['title'], 20),
                  'body': shorten_blog_body(row['body']),
                  'time_display': time_decide(row['time_create'], row['time_edit'], '%Y-%m-%d'),
                  'time_datetime_attr': time_decide(row['time_create'], row['time_edit']),
                  '_created': row['time_create'],
                  '_edited': row['time_edit'],
                  '_pv': int(row['pv'])}
        blogs.append(_blogs)

    # SORT_TYPE
    if sort_type == "date_desc":
        blogs.sort(key=lambda x: x['_created'], reverse=True)
    elif sort_type == "edit_desc":
        blogs.sort(key=lambda x: x['_edited'], reverse=True)
    elif sort_type == "popular":
        blogs.sort(key=lambda x: x['_pv'], reverse=True)
    else:
        # TODO: 使用默认策略, 按照表中ID
        pass

    # FLAG_MINE_ONLY
    if flag_mine_only:
        uid = session.get('uid', None)
        if uid is not None:
            blogs = [_ for _ in blogs if _['author'] == uid]

    return render_template('blog.html',
                           blog_entry_list=blogs,
                           sidebar_default_value=sidebar_default_value)


def blog_sort_filter(lst, sort_type, search_keyword, flag_mine_only):
    pass

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
    g.con = db_open()
    blog_detail = g.con.execute("SELECT blog.*, user.username "
                                "FROM blog LEFT JOIN user "
                                "ON blog.author_id = user.id "
                                "WHERE blog.id=?", (bid,)).fetchone()
    if not blog_detail:
        abort(404)
    if blog_detail['deleted_at'] is not None:
        abort(404)

    if increase_pv(bid):
        g.con.execute("UPDATE blog SET pv=pv+1 WHERE id=?", (bid,))
        g.con.commit()
        blog_detail['pv'] += 1

    time_create, time_edit = blog_detail['created'], blog_detail['edited']
    if time_edit > time_create:
        blog_detail['release_type'] = "编辑于"
        blog_detail['time_datetime_attr'] = time_edit.strftime('%Y-%m-%d %H:%M:%S')
        blog_detail['time_display'] = time_edit.strftime('%Y-%m-%d %H:%M')
    else:
        blog_detail['release_type'] = "发布于"
        blog_detail['time_datetime_attr'] = time_create.strftime('%Y-%m-%d %H:%M:%S')
        blog_detail['time_display'] = time_create.strftime('%Y-%m-%d %H:%M')

    return render_template('blog_detail.html', blog_entry=blog_detail)


def increase_pv(bid):
    # unauthenticate user doesn't count
    if session.get('uid', None) is None:
        return False

    # user has no history
    if session.get('history', None) is None:
        session['history'] = [bid]
        return True

    # user has history
    current_app.logger.info(f"user({session['uid']}): history: {session['history']}")
    if bid in session.get('history'):
        return False
    else:
        _ = session['history']
        session.pop('history')
        session['history'] = _ + [bid]
        return True


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

    # error code 2004: blog is deleted
    current_app.logger.info(f"[BLOG-AUTH] {cur=}")
    if 'deleted_at' in cur and cur['deleted_at'] is not None:
        return 2004, f'blog is deleted at {cur["deleted_at"].strftime(f"%Y-%m-%d %H:%M:%S")}', 404

    # error code 20001: not login, which will logged as ERROR because this SHOULD DEFINITELY NOT HAPPEN
    uid = session.get('uid', None)
    if uid is None:
        current_app.logger.error(f"[blog-authenticate-and-authorize]: user not logged in")
        return 20001, 'no user login info', 401

    # error code 20003: blog author != current user, unauthorized
    if cur['author_id'] != uid:
        return 20003, 'unauthorized, user is not blog author', 403

    return 0, 'auth and auth', 200
