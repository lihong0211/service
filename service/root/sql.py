# service/root/sql.py
"""
词根相关的SQL语句
"""

ROOT_SQL = {
    # 增
    "root_insert": (
        "INSERT INTO root (id, name, meaning, similar, cases) "
        "VALUES(0, %s, %s, %s, %s)"
    ),
    # 删
    "root_delete": "DELETE FROM root WHERE id=%s",
    # 改
    "root_update": (
        "UPDATE root SET name=%s, meaning=%s, similar=%s, cases=%s WHERE id=%s"
    ),
    # 查
    "root_list": "SELECT * FROM root",
}

