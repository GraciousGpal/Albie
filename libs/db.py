import logging
from sqlite3 import Error, connect

log = logging.getLogger(__name__)


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = connect(db_file)
        # Set journal mode to WAL.
        conn.execute('pragma journal_mode=wal')
    except Error as e:
        log.error(e)
    return conn
