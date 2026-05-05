from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, abort, current_app, g
from steve_site.auth import force_login
from steve_site.db_api import db_open
import nh3
import mistune


markdown_converter = mistune.create_markdown(plugins=['strikethrough', 'table', 'task_lists', 'mark', 'math', 'spoiler'],
                                             renderer='html')
bp = Blueprint('blog', __name__, url_prefix='/blog')


nh3_allowed_tags = nh3.ALLOWED_TAGS | {"input", }
nh3_allowed_attributes = {
    "li": {"class"},
    "input": {
        "class",
        "type",
        "disabled",
        "checked"
    }
}


graph_transition = {
    'DRAFT': {'publish':    (('Author',),               'PUBLIC'),
              'delete':     (('Author',),               'DELETED'),
              'edit':       (('Author',),               'DRAFT'),
              'view':       (('Author',),               None)},

    'PUBLIC': {'hide':      (('Admin', 'Operator'),     'HIDDEN'),
               'delete':    (('Author',),               'DELETED'),
               'edit':      (('Author',),               'PUBLIC'),
               'view':      (('Guest', 'User', 'Operator', 'Admin'), None)},

    'DELETED': {'restore':  (('Admin',),                'PUBLIC'),
                'view':     (('Admin',),                None)},

    'PENDING': {'delete':   (('Author',),               'DELETED'),
                'submit':   (('Author',),               'HIDDEN'),
                'edit':     (('Author',),               'PENDING'),
                'view':     (('Author', 'Admin'),       None)},

    'HIDDEN': {'publish':   (('Admin', 'Operator'),     'PUBLIC'),
               'restore':   (('Admin',),                'PENDING'),
               'delete':    (('Author',),               'DELETED'),
               'view':      (('Author', 'Operator', 'Admin'), None)}
}


def shorten_blog_title(s, limit):
    if len(s) <= limit:
        return s
    limit = (limit-4)//2
    return f"{s[:limit]}...{s[-limit:]}"


def shorten_blog_body(s, limit=70):
    if len(s) <= limit:
        return s
    return s[:limit] + '...[点击查看全文]'


def time_later(t1, t2, fmt=f'%Y-%m-%d %H:%M:%S'):
    return t1 if t1 >= t2 else t2


def get_current_user():
    uid = session.get('uid', None)
    if uid is None:
        return None, 'Guest'
    db_open()
    cur = g.con.execute("SELECT level FROM user WHERE id=?", (uid,)).fetchone()
    return uid, cur['level']


def is_blog_visible(blog):
    uid, role = get_current_user()
    visible_roles = graph_transition[blog['status']]['view'][0]
    if role in visible_roles:
        return True
    elif 'Author' in visible_roles and uid==blog['author_id']:
        return True
    else:
        return False


def blog_body_convert(s):
    current_app.logger.info(f"original content: {s}")
    s = markdown_converter(s)

    # This is nonsense cause mistune.Markdown with renderer=HTML will return str only
    # Just to make pylint happy
    if not isinstance(s, str):
        s = str(s)

    current_app.logger.info(f"converted content: {s}")
    s = nh3.clean(s, attributes=nh3_allowed_attributes, tags=nh3_allowed_tags)
    current_app.logger.info(f"cleaned content: {s}")
    return s


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


def get_action_list(blog_detail):
    uid, user_level = get_current_user()
    if uid is None:
        return []
    current_app.logger.info(f"<get_action_list> {uid=}, {user_level=}, {blog_detail['status']=}")
    res = set()
    possible_action = graph_transition[blog_detail['status']]
    for action, (role_tuple, status_next) in possible_action.items():
        if user_level in role_tuple:
            res.add(action)
        if uid == blog_detail['author_id'] and 'Author' in role_tuple:
            res.add(action)

    return list(res)


def handle_transition(bid, action):
    g.con = db_open()

    # ERROR: blog not exist
    cur = g.con.execute("SELECT author_id, status FROM blog WHERE id=?", (bid,)).fetchone()
    if not cur:
        return 20002, f'[TransitionError] non-exist {bid=}', 404
    else:
        author_id = cur['author_id']
        status = cur['status']

    # ERROR: user not login
    uid = session.get('uid', None)
    if uid is None:
        current_app.logger.error(f"[blog-authenticate-and-authorize]: user not logged in")
        return 20001, '[TransitionError] no user login info', 401
    else:
        cur = g.con.execute("SELECT level FROM user WHERE id=?", (uid,)).fetchone()
        level = cur['level']

    curr_status_dict = graph_transition[status]
    if action not in curr_status_dict:
        return 20031, f'[TransitionError-Conflicting action] cannot {action} a <{status}> blog', 409

    required_role, status_dst = curr_status_dict[action]
    if level in required_role:
        return 0, status_dst, 200
    elif author_id == uid and 'Author' in required_role:
        return 0, status_dst, 200
    else:
        return 20032, (f'[TransitionError-Unauthorized] current user ({uid=}, {level=}, is_author={author_id == uid}) '
                       f'cannot {action} a <{status}> blog'), 403


def verify_action(action):
    def _verify_action(f):

        @wraps(f)
        def __verify_action(*args, **kwargs):
            bid = kwargs['bid']
            error_code, desc, status_code = handle_transition(bid, action)
            if error_code:
                current_app.logger.error(f"[blog-{f.__name__}] {action=}, {error_code=}, {desc=}")
                return redirect(url_for(f"status_page_{status_code}"), code=303)
            return f(*args, **kwargs)

        return __verify_action
    return _verify_action


@bp.get('/')
def index():
    # parse GET request args if possible
    sort_type = request.args.get('sort', None)
    search_keyword = request.args.get('keyword', None)
    flag_mine_only = request.args.get('my_posts') == 'on'

    # set default value for render template
    sidebar_default_value = {'sort_type': sort_type,
                             'search_keyword': search_keyword,
                             'flag_mine_only': flag_mine_only}
    if flag_mine_only and session.get('uid', None) is None:
        sidebar_default_value['flag_mine_only'] = False

    # define SEARCH_KEYWORD for SQLite
    if search_keyword is None or search_keyword.strip() == '':
        sql_search = ""
    else:
        sql_search = (f" WHERE title LIKE '%{search_keyword}%' OR"
                      f" body LIKE '%{search_keyword}%'")

    # GET BLOG LIST
    g.con = db_open()
    res = g.con.execute('SELECT blog.*, user.username AS author '
                        'FROM blog '
                        'LEFT JOIN user '
                        'ON blog.author_id = user.id'
                        f'{sql_search}').fetchall()
    blogs = [_ for _ in res if is_blog_visible(_)]

    # blogs -H (Human-Readable)
    for blog in blogs:
        blog['title'] = shorten_blog_title(blog['title'], 20)
        blog['body'] = shorten_blog_body(blog['body'])
        time_display = time_later(blog['created'], blog['edited'])
        blog['time_display'] = time_display.strftime('%Y-%m-%d')
        blog['time_datetime_attr'] = time_display

    # FILTER
    if flag_mine_only:
        uid = session.get('uid', None)
        if uid is not None:
            blogs = [_ for _ in blogs if _['author_id'] == uid]

    # SORT_TYPE
    if sort_type == "date_desc":
        blogs.sort(key=lambda x: x['created'], reverse=True)
    elif sort_type == "edit_desc":
        blogs.sort(key=lambda x: x['edited'], reverse=True)
    elif sort_type == "popular":
        blogs.sort(key=lambda x: x['pv'], reverse=True)
    else:
        # TODO: 使用默认策略, 按照表中ID
        pass

    return render_template('blog.html',
                           blog_entry_list=blogs,
                           sidebar_default_value=sidebar_default_value)


# NULL -> DRAFT/PUBLIC
@bp.route('/add', methods=["GET", "POST"])
@force_login
def add():
    # GET method
    if request.method == 'GET':
        return render_template('blog_editor.html', submit_href=url_for("blog.add"))

    # POST method
    title = request.form['title']
    content = request.form['content']
    action = request.form['action']
    if action == 'publish':
        status = 'PUBLIC'
    elif action == 'save':
        status = 'DRAFT'
    else:
        abort(403)

    uid = session.get('uid')
    g.con = db_open()
    cur = g.con.execute("INSERT INTO blog (author_id, title, body, status) "
                      "VALUES (?, ?, ?, ?) "
                      "RETURNING id",
                      (uid, title, content, status))
    blog_id = cur.fetchone()['id']
    g.con.commit()
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
    if not is_blog_visible(blog_detail):
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

    # convert title
    blog_detail['body'] = blog_body_convert(blog_detail['body'])
    blog_detail['title'] = nh3.clean(blog_detail['title'])

    # edit, delete, publish, restore, hide, submit
    return render_template('blog_detail.html',
                           blog_entry=blog_detail,
                           manage_list=get_action_list(blog_detail))


@bp.route('/<int:bid>/delete', methods=['DELETE'])
@force_login
@verify_action('delete')
def delete(bid):
    g.con = db_open()
    g.con.execute("UPDATE blog SET deleted_at=CURRENT_TIMESTAMP, status='DELETED' WHERE id = ?", (bid,))
    g.con.commit()
    return redirect(url_for('blog.index'), code=303)


@bp.route('/<int:bid>/publish', methods=['POST'])
@force_login
@verify_action('publish')
def publish(bid):
    g.con = db_open()
    g.con.execute("UPDATE blog SET status='PUBLIC' WHERE id = ?", (bid,))
    g.con.commit()
    return redirect(url_for('blog.view', bid=bid))


@bp.route('/<int:bid>/submit', methods=['POST'])
@force_login
@verify_action('submit')
def submit(bid):
    g.con = db_open()
    g.con.execute("UPDATE blog SET status='HIDDEN' WHERE id = ?", (bid,))
    g.con.commit()
    return redirect(url_for('blog.view', bid=bid))


@bp.route('/<int:bid>/hide', methods=['POST'])
@force_login
@verify_action('hide')
def hide(bid):
    g.con = db_open()
    g.con.execute("UPDATE blog SET status='HIDDEN' WHERE id = ?", (bid,))
    g.con.commit()
    return redirect(url_for('blog.view', bid=bid))


@bp.route('/<int:bid>/restore', methods=['POST'])
@force_login
@verify_action('restore')
def restore(bid):
    g.con = db_open()
    status = g.con.execute("SELECT status FROM blog WHERE id = ?", (bid,)).fetchone()['status']
    if status == 'DELETED':
        g.con.execute("UPDATE blog SET deleted_at=NULL, status='PUBLIC' WHERE id = ?", (bid,))
    elif status == 'HIDDEN':
        g.con.execute("UPDATE blog SET status='PENDING' WHERE id = ?", (bid,))
    else:
        return abort(409)

    g.con.commit()
    return redirect(url_for('blog.view', bid=bid))


@bp.route('/<int:bid>/edit', methods=["GET", "POST"])
@force_login
@verify_action('edit')
def edit(bid):
    g.con = db_open()

    # GET method
    if request.method == 'GET':
        data = g.con.execute("SELECT title, body, status FROM blog WHERE id = ?", (bid,)).fetchone()
        if data['status'] == 'PENDING':
            submit_mode = 'save-only'
        elif data['status'] == 'PUBLIC':
            submit_mode = "publish-only"
        elif data['status'] == 'DRAFT':
            submit_mode = "default"
        else:
            submit_mode = "default"
        return render_template('blog_editor.html',
                               blog_detail=data,
                               submit_href=url_for("blog.edit", bid=bid),
                               submit_mode=submit_mode)

    # POST method
    title = request.form['title']
    content = request.form['content']
    action = request.form['action']

    if action == 'save':
        g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP WHERE id=?", (title, content, bid))
        g.con.commit()
        return redirect(url_for('blog.view', bid=bid))
    elif action == 'publish':
        g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP, status='PUBLIC' WHERE id=?", (title, content, bid))
        g.con.commit()
        return redirect(url_for('blog.view', bid=bid))
    else:
        return abort(409)
