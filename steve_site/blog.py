from functools import wraps
import re
from flask import Blueprint, render_template, request, redirect, url_for, session, abort, current_app, g, jsonify
from steve_site.auth import force_login
from steve_site.db_api import db_open
import nh3
import mistune
from urllib.parse import urlparse


markdown_converter = mistune.create_markdown(plugins=['strikethrough', 'table', 'task_lists', 'mark', 'math', 'spoiler'],
                                             renderer='html')
bp = Blueprint('blog', __name__, url_prefix='/blog')


nh3_allowed_tags = nh3.ALLOWED_TAGS | {"input", "img"}
nh3_allowed_attributes = {
    "li": {"class"},
    "input": {
        "class",
        "type",
        "disabled",
        "checked"
    },
    "img": {
        "src",
        "alt"
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

    return render_template('blog/blog.html',
                           blog_entry_list=blogs,
                           sidebar_default_value=sidebar_default_value)


# NULL -> DRAFT/PUBLIC
@bp.route('/add', methods=["GET", "POST"])
@force_login
def add():
    # GET method
    if request.method == 'GET':
        return render_template('blog/blog_editor.html',
                               submit_href=url_for("blog.add"),
                               action_btn_list=['save', 'publish'],
                               unique_id=f"uid_{session.get('uid')}_blog_new")

    # POST method
    data = request.get_json()
    current_app.logger.debug(data)
    if not data:
        return jsonify({"status": "error", "message": "Empty JSON"}), 500
    title = data.get('title')
    content = data.get('content')
    action = data.get('action')
    if action == 'publish':
        status = 'PUBLIC'
    elif action == 'save':
        status = 'DRAFT'
    else:
        abort(403)

    uid = session.get('uid')
    g.con = db_open()
    cover_url = extract_cover_url(content)
    cur = g.con.execute("INSERT INTO blog (author_id, title, body, status, cover_url) "
                      "VALUES (?, ?, ?, ?, ?) "
                      "RETURNING id",
                      (uid, title, content, status, cover_url))
    blog_id = cur.fetchone()['id']
    g.con.commit()
    return jsonify({"status": "success",
                    "redirect_url": url_for('blog.view', bid=blog_id),
                    "msg": "提交成功喵!"}), 200

# TODO
""" 
修正二：给“取消/返回”按钮加特效（清理幽灵草稿）
在你的博客编辑页面，肯定有“取消”、“返回”或“丢弃”按钮。不要让用户直接跳转，而是给按钮绑定一个点击事件，主动去擦除这个特定键名的 LocalStorage：

JavaScript
// 当用户点击“放弃编写/返回”按钮时
document.getElementById('cancel-btn').addEventListener('click', function() {
    // 1. 如果 EasyMDE 提供了自带的内置清空方法：
    if (easyMDE.autosave) {
        localStorage.removeItem('smde_user_' + currentUid + '_blog_new');
    }
    // 2. 然后再跳转回首页
    window.location.href = '/dashboard';
});
"""


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
    return render_template('blog/blog_detail.html',
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
    data = g.con.execute("SELECT title, body, status FROM blog WHERE id = ?", (bid,)).fetchone()
    if data['status'] == 'PENDING':
        action_btn_list = ['save', 'submit']
    elif data['status'] == 'PUBLIC':
        action_btn_list = ['publish']
    elif data['status'] == 'DRAFT':
        action_btn_list = ['save', 'publish']
    else:
        action_btn_list = []

    # GET method
    if request.method == 'GET':
        return render_template('blog/blog_editor.html',
                               blog_detail=data,
                               submit_href=url_for("blog.edit", bid=bid),
                               action_btn_list=action_btn_list,
                               unique_id=f"uid_{session.get('uid')}_blog_{bid}")

    # POST method
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "Empty JSON"}), 500
    _ = [data.get(k, None) for k in ('title', 'content', 'action')]
    if None in _:
        return jsonify({"status": "error", "msg": "Malformed JSON"}), 500
    title, content, action = _
    current_app.logger.info(f"{title=}, {content=}, {action=}")
    if action not in action_btn_list:
        return jsonify({"status": "error", "msg": "unknown action type"}), 409

    if title.strip() == '':
        return jsonify({"status": "error", "msg": "empty title"}), 400

    cover_url = extract_cover_url(content)
    if action == 'save':
        g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP, cover_url=?"
                      "WHERE id=?",
                      (title, content, cover_url, bid))
    elif action == 'publish':
        g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP, status='PUBLIC', cover_url=?"
                      "WHERE id=?",
                      (title, content, cover_url, bid))
    elif action == 'submit':
        g.con.execute("UPDATE blog SET title=?, body=?, edited=CURRENT_TIMESTAMP, status='HIDDEN', cover_url=?"
                      "WHERE id=?",
                      (title, content, cover_url, bid))

    g.con.commit()
    return jsonify({"status": "success",
                    "redirect_url": url_for('blog.view', bid=bid),
                    "msg": "编辑成功喵!"}), 200


def extract_cover_url(body):
    R2_CUSTOM_DOMAIN = current_app.config['R2_CUSTOM_DOMAIN']

    # get first ![](<url>) as cover
    url_list = re.findall(r"!\[.*\]\((?P<url>.+)\)", body)
    if not url_list:
        return ''

    for url in url_list[:5]:
        # verify URL valid
        try:
            parse_res = urlparse(url)
            if parse_res.scheme not in ('http', 'https') or not parse_res.netloc:
                continue
            if any(char in parse_res.netloc for char in (' ', '\n', '\r', '\t')):
                continue

        except Exception as e:
            current_app.logger.info(f'{e=}')
            continue

        # check if url is from my R2 bucket
        res = re.match(R2_CUSTOM_DOMAIN + r"/\d+/\d{4}/\d{2}/(?P<image_uuid>.{8})_(?P<image_type>(thumb|small|large)).webp",
                       url)
        if not res:
            return url

        # check exists in DB; if uuid exists, try to replace large/small with thumb
        uuid = res.group('image_uuid')
        thumb_type = res.group('image_type')
        res = g.con.execute("SELECT * FROM image WHERE uuid = ? AND status = 'NORMAL'", (uuid,)).fetchone()
        if not res:
            continue
        if thumb_type not in res['url_and_size']:
            continue
        else:
            return res['url_and_size']['thumb']['url']  # valid URL, return thumb url

    return ''
