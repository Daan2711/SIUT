from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles

db = SQLAlchemy()


@compiles(BigInteger, 'sqlite')
def _biginteger_en_sqlite(_tipo, _compilador, **_kw):
    """Solo para SQLite (desarrollo local y pruebas).

    Los modelos usan BigInteger como en Neon, pero en SQLite solo una columna
    INTEGER PRIMARY KEY es autoincremental. No afecta a PostgreSQL.
    """
    return 'INTEGER'
