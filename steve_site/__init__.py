from flask import Flask, render_template, request, abort
import os
from steve_site import db_api, auth, blog, image
from steve_site.otp_manager import OTPManager


def create_inst_path(inst_path):
    if not os.path.exists(inst_path):
        os.makedirs(inst_path)


def create_app():
    app = Flask(__name__, static_folder="static")

    # +-----------------------------+
    # |     Instance Config Map     |
    # +-----------------------------+
    app.config.from_pyfile('config.py')
    app.config['DB'] = os.path.join(app.instance_path, app.config['DB_FILENAME'])
    app.otp_manager = OTPManager(app)

    # +-------------------------------------+
    # |     Create Instance Path and DB     |
    # +-------------------------------------+
    create_inst_path(app.instance_path)
    db_api.db_create(app)

    # +----------------------------------------+
    # |     Register Blueprint, CLI, etc.      |
    # +----------------------------------------+
    db_api.db_register(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(blog.bp)
    app.register_blueprint(image.bp)

    # +-------------------------------------------+
    # |     Register status code pages, etc.      |
    # +-------------------------------------------+
    @app.errorhandler(404)
    def error_404(error):
        return render_template('404.html'), 404

    @app.route('/404')
    def status_page_404():
        return render_template('404.html'), 404

    @app.errorhandler(401)
    def error_401(error):
        return render_template('401.html'), 401

    @app.route('/401')
    def status_page_401():
        return render_template('401.html'), 401

    @app.errorhandler(403)
    def error_403(error):
        return render_template('403.html'), 403

    @app.route('/403')
    def status_page_403():
        return render_template('403.html'), 403

    @app.errorhandler(405)
    def error_405(error):
        return render_template('405.html'), 405

    @app.route('/405')
    def status_page_405():
        return render_template('405.html'), 405

    @app.errorhandler(409)
    def error_409(error):
        return render_template('409.html'), 409

    @app.route('/409')
    def status_page_409():
        return render_template('409.html'), 409

    # +-------------------+
    # |     UA verify     |
    # +-------------------+
    @app.before_request
    def check_ua():
        ua = request.headers.get('User-Agent', None)
        if ua is None:
            return

        ua = ua.lower()
        keywords = ('bot', 'spider', 'crawler', 'python', 'selenium', 'fetch', 'slurp')
        for keyword in keywords:
            if keyword in ua:
                abort(418)

    # +--------------------+
    # |     Index View     |
    # +--------------------+
    @app.route('/')
    def resp_index():
        return render_template("index.html")

    return app
