# service/affix/sql.py
"""
词缀相关的SQL语句
"""

AFFIX_SQL = {
    # 增
    "affix_insert": (
        "INSERT INTO affix (id, name, meaning, similar, cases) "
        "VALUES(0, %s, %s, %s, %s)"
    ),
    # 删
    "affix_delete": "DELETE FROM affix WHERE id=%s",
    # 改
    "affix_update": (
        "UPDATE affix SET name=%s, meaning=%s, similar=%s, cases=%s WHERE id=%s"
    ),
    # 查
    "affix_list": "SELECT * FROM affix",
}

