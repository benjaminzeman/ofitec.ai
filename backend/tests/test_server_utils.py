from flask import Flask
import sqlite3
import server_utils as su


def test_list_routes_basic():
    app = Flask(__name__)

    @app.get('/ping')
    def _ping():  # noqa: D401
        return {'ok': True}

    @app.post('/echo')
    def _echo():  # noqa: D401
        return {'x': 1}

    routes = su.list_routes(app)
    # Expect two routes sorted by rule
    rules = [r['rule'] for r in routes]
    assert '/echo' in rules and '/ping' in rules
    for r in routes:
        assert isinstance(r['methods'], list)


def test_db_objects_and_exists():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()
    cur.execute('CREATE TABLE demo(id INTEGER)')
    cur.execute('CREATE VIEW demo_v AS SELECT id FROM demo')
    objs = su.list_db_objects(con)
    names = {o['name'] for o in objs}
    assert {'demo', 'demo_v'} <= names
    assert su.table_exists(con, 'demo') is True
    assert su.table_exists(con, 'nope') is False


def test_normalize_project_name():
    assert su.normalize_project_name(None) is None
    assert su.normalize_project_name('   ') is None
    assert su.normalize_project_name('null') is None
    assert su.normalize_project_name(' Proyecto X ') == 'Proyecto X'
