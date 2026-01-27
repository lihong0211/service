# service/livingSpeech/sql.py
"""
生活用语相关的SQL语句
"""

LIVING_SPEECH_SQL = {
    # 增
    'insert': 'INSERT INTO livingSpeech (id, speech, meaning) VALUES(0, %s, %s)',
    # 删
    'delete': 'DELETE FROM livingSpeech WHERE id=%s',
    # 改
    'update': 'UPDATE livingSpeech SET speech=%s, meaning=%s WHERE id=%s',
    # 查
    'list': 'SELECT * FROM livingSpeech',
}


