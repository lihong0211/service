# service/peach/version/sql.py
"""
版本相关的SQL语句
"""

VERSION_SQL = {
    'insert': (
        'INSERT INTO version (version, name, platform) VALUES (%s, %s, %s) '
        'ON DUPLICATE KEY UPDATE version = VALUES(version)'
    ),
    'list': 'SELECT * FROM version',
}


