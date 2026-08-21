"""Connection helper and the migration runner (~30 lines).

Records applied migrations in a `schema_migrations` table from day one.
"""


def connect():
    """Open a connection to DATABASE_URL."""
    raise NotImplementedError


def migrate():
    """Apply every unapplied file in migrations/ in filename order, in a
    transaction each, recording the name in schema_migrations."""
    raise NotImplementedError
