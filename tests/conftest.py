import os
import tempfile
import uuid
import pytest
from dotenv import load_dotenv
import steve_site
from steve_site.db_api import db_open
from werkzeug.security import generate_password_hash
from tests.client_actor import ClientActor


load_dotenv()


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def app(assign_sql_filepath, assign_redis_db_num):
    app = steve_site.create_app(env_type='test', config={'DB': assign_sql_filepath,
                                                         'REDIS_DB_NUM': assign_redis_db_num})
    app.test_client_class = ClientActor
    return app


@pytest.fixture(scope="session")
def assign_redis_db_num():
    worker_id = os.environ.get('PYTEST_XDIST_WORKER')
    if worker_id and worker_id != 'master':
        db_num = int(worker_id.replace('gw', ''))
    else:
        db_num = 0
    return db_num


@pytest.fixture(scope="session")
def assign_sql_filepath():
    tmp_dir = tempfile.gettempdir()
    tmp_filename = f"{uuid.uuid4().hex}.db"
    tmp_file = os.path.join(tmp_dir, tmp_filename)

    yield tmp_file

    os.remove(tmp_file)


@pytest.fixture(scope="function", autouse=True)
def flush_redis(app, assign_redis_db_num):
    r = app.config['SESSION_REDIS']
    r.flushdb()
    yield
    r.flushdb()


@pytest.fixture(scope="function", autouse=True)
def flush_sql(app, user_info, blog_info):
    def _truncate():
        table_list = ['user', 'blog', 'user_modify_tmp']
        with app.app_context():
            con = db_open()
            for table in table_list:
                con.execute(f"DELETE FROM {table}")
            for table in table_list:
                con.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            con.commit()

    def _rebuild():
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

    _truncate()
    _rebuild()
    yield
    _truncate()
