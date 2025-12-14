from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from steve_site.db_api import db_open


bp = Blueprint('blog', __name__, url_prefix='/blog')


@bp.route('/')
def index():
    return render_template('blog.html')

@bp.route('/add')
def blog_add():
    return render_template('blog_editor.html')

@bp.route('/edit/<int:id>')
def blog_edit(bid):
    return render_template('blog_editor.html')

@bp.route('/delete/<int:id>')
def blog_delete(bid):
    return render_template(url_for('blog.index'))

@bp.route('/blog/<int:id>')
def blog_view(bid):
    return render_template('blog_detail.html')

@bp.route('/test_view')
def blog_test():
    return render_template('blog_detail.html')

@bp.route('/test_edit')
def blog_edit_test():
    return render_template('blog_editor.html')