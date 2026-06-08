import pytest


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
def get_client(user_info, app):
    def _get_client(user_level):
        for uid, info in user_info.items():
            if info['level'] != user_level:
                continue

            client = app.test_client()
            client.login(info['username'], info['password'])
            return uid, info, client
        raise SyntaxError
    return _get_client


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
        client.blog_view(bid, blog_info, expect_res)
    elif action == 'delete':
        client.blog_delete(app, bid, expect_res)
    elif action == 'publish':
        client.blog_publish(app, bid, expect_res)
    elif action == 'submit':
        client.blog_submit(app, bid, expect_res)
    elif action == 'hide':
        client.blog_hide(app, bid, expect_res)
    elif action == 'restore':
        client.blog_restore(app, bid, expect_res)
    elif action == 'edit-get':
        client.blog_edit_get(app, bid, expect_res)
    elif action == 'edit-publish':
        client.blog_edit_publish(app, bid, expect_res)
    elif action == 'edit-save':
        client.blog_edit_save(app, bid, expect_res)
    elif action == 'edit-submit':
        client.blog_edit_submit(app, bid, expect_res)
