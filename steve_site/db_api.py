import os.path
import click
from flask import g, current_app, Flask
import sqlite3
import time


def factory_func(cursor, row):
    field = [col[0] for col in cursor.description]
    current_app.logger.info(f"[factory_func] {field=}, {row=}")
    return dict(zip(field, row))


def db_open():
    db_path = current_app.config['DB']
    if not os.path.exists(db_path):
        current_app.logger.error('try to open a missing db file')
        raise OSError('try to open a missing db file')

    g.db = sqlite3.connect(db_path)
    g.db.row_factory = factory_func
    return g.db


def db_close(e):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def db_create(app):
    db_path = app.config['DB']
    if os.path.exists(db_path):
        app.logger.warning('Instance DB already already exists')
        return

    app.logger.info('Create new instance DB')
    with app.open_resource("schema.sql") as f:
        con = sqlite3.connect(db_path)
        con.executescript(f.read().decode('utf8'))
        con.close()

@click.command("db-backup")
def db_backup():
    src = db_open()
    dst = sqlite3.connect(os.path.join(current_app.instance_path,
                                       f'inst_runtime_{time.strftime("%Y_%m_%d__%H_%M_%S")}.db'))
    src.backup(dst)
    dst.close()

def db_register(app: Flask):
    app.cli.add_command(db_backup)
    app.teardown_appcontext(db_close)
