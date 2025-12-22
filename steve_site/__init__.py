from flask import Flask, render_template
import os
from steve_site import db_api, auth, blog


def create_inst_path(inst_path):
    if not os.path.exists(inst_path):
        os.makedirs(inst_path)


def create_app():
    app = Flask(__name__, static_folder="static")

    # +-----------------------------+
    # |     Instance Config Map     |
    # +-----------------------------+
    app.config.from_mapping(SECRET_KEY='dev',
                            DB=os.path.join(app.instance_path, 'inst_runtime.db'))

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

    # +----------------------------------------+
    # |     Register Blueprint, CLI, etc.      |
    # +----------------------------------------+
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html'), 404


    # +-------------------+
    # |     Test View     |
    # +-------------------+
    @app.route('/test')
    def resp_test():
        return "Hello, world!"

    # +--------------------+
    # |     Index View     |
    # +--------------------+
    @app.route('/')
    def resp_index():
        return render_template("index.html")

    return app
