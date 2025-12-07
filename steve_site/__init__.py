from flask import Flask, render_template
import os
from steve_site import db_api, auth, list_api


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
    # db_api._db_create(app)

    # +----------------------------------------+
    # |     Register Blueprint, CLI, etc.      |
    # +----------------------------------------+
    # db_api._db_register(app)
    # app.register_blueprint(auth.bp)
    # app.register_blueprint(list_api.bp)
    # 1


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
