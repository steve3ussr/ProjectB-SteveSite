import time
from logging.handlers import RotatingFileHandler
import boto3
import redis
from botocore.config import Config
from flask import Flask, render_template, request, abort, current_app
import os
import sys
import logging
from flask_session import Session
from steve_site import db_api, auth, blog, image
from steve_site.otp_manager import OTPManager
from steve_site.release_notes import get_release_note_html


def create_inst_path(inst_path):
    if not os.path.exists(inst_path):
        os.makedirs(inst_path)


def modify_logger_for_prod(app):
    #
    log_formatter = logging.Formatter('[%(asctime)s] %(levelname)-7s in %(filename)s (%(funcName)s:%(lineno)d): %(message)s')

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)

    log_dir = os.path.join(app.instance_path, app.config['LOG_DIR'])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    file_handler = RotatingFileHandler(os.path.join(log_dir, f"{time.strftime('%Y%m%d-%H%M%S')}.log"),
                                       maxBytes=20 * 1024 * 1024,
                                       backupCount=5)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.WARNING)

    logging.getLogger('flask.app').setLevel(logging.INFO)
    logging.getLogger('waitress.queue').setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    app.logger.handlers = []

    app.logger.warning(f"{log_dir=}")


def create_app(*args, env_type=None, config=None):
    app = Flask(__name__, static_folder="static")

    # +-----------------------------+
    # |     Instance Config Map     |
    # +-----------------------------+
    if app.config['DEBUG']:
        app.config.from_object('steve_site.config.DevConfig')
    elif env_type == 'test' or app.config['TESTING']:
        app.config.from_object('steve_site.config.TestConfig')
        app.config['TESTING'] = True
    else:
        app.config.from_object('steve_site.config.ProdConfig')
    if config is not None:
        app.config.from_mapping(config)

    # +-------------+
    # |     LOG     |
    # +-------------+

    if app.config['TESTING']:
        pass
    elif app.config['DEBUG']:
        # modify_logger_for_prod(app)
        pass
    else:
        modify_logger_for_prod(app)

    # +---------------------------+
    # |     SQLite + Redis DB     |
    # +---------------------------+

    # determine DB at runtime
    if 'DB' not in app.config:
        db_filename = app.config['DB_FILENAME']
        app.config['DB'] = os.path.join(app.instance_path, db_filename)

    # determine Redis DB at runtime
    url = f"{app.config['REDIS_BASE_URL']}/{app.config['REDIS_DB_NUM']}"
    app.config['SESSION_REDIS'] = redis.Redis.from_url(url)
    app.logger.warning(f"redis url: {url}")

    # +--------------------------------+
    # |     OTP, R2, Flask-Session     |
    # +--------------------------------+
    app.otp_manager = OTPManager(app)
    Session(app)
    app.r2_client = boto3.client(
        service_name='s3',
        endpoint_url=f'https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com',
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4'))

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
        return render_template('status-code/404.html'), 404

    @app.route('/404')
    def status_page_404():
        return render_template('status-code/404.html'), 404

    @app.errorhandler(401)
    def error_401(error):
        return render_template('status-code/401.html'), 401

    @app.route('/401')
    def status_page_401():
        return render_template('status-code/401.html'), 401

    @app.errorhandler(403)
    def error_403(error):
        return render_template('status-code/403.html'), 403

    @app.route('/403')
    def status_page_403():
        return render_template('status-code/403.html'), 403

    @app.errorhandler(405)
    def error_405(error):
        return render_template('status-code/405.html'), 405

    @app.route('/405')
    def status_page_405():
        return render_template('status-code/405.html'), 405

    @app.errorhandler(409)
    def error_409(error):
        return render_template('status-code/409.html'), 409

    @app.route('/409')
    def status_page_409():
        return render_template('status-code/409.html'), 409

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

    # +--------------------------------+
    # |     Cache Static Resources     |
    # +--------------------------------+
    @app.after_request
    def cache_static_resources(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-cache'
        return response

    # +--------------------+
    # |     Index View     |
    # +--------------------+
    @app.route('/')
    def resp_index():
        return render_template("index.html",
                               release_note_html=get_release_note_html(limit=4))

    return app



