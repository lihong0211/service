# service/dialogue/sql.py
"""
对话相关的SQL语句
"""

DIALOGUE_SQL = {
    # 增
    "dialogue_insert": (
        "INSERT INTO dialogue (id, dialogue, meaning, words, section) "
        "VALUES(0, %s, %s, %s, %s)"
    ),
    # 删
    "dialogue_delete": "DELETE FROM dialogue WHERE id=%s",
    # 改
    "dialogue_update": (
        "UPDATE dialogue SET dialogue=%s, meaning=%s, words=%s, section=%s WHERE id=%s"
    ),
    # 查
    "dialogue_list": "SELECT * FROM dialogue",
}

