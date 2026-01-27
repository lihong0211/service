# service/peach/pluginStatistic/sql.py
"""
插件统计相关的SQL语句
"""

PLUGIN_STATISTIC_SQL = {
    'update': (
        'UPDATE plugin_statistic '
        'SET logout_time = NOW(), status = \'offline\' '
        'WHERE user_name = %s AND status = \'online\''
    ),
    'insert': (
        'INSERT INTO plugin_statistic '
        '(user_name, platform, plugin_version, login_time, status) '
        'VALUES (%s, %s, %s, NOW(), %s)'
    ),
    'detail': (
        'SELECT '
        'user_name, '
        'platform, '
        'plugin_version, '
        'SEC_TO_TIME(duration) AS duration, '
        'DATE_FORMAT(login_time, \'%Y-%m-%d %H:%i:%s\') AS login_time, '
        'DATE_FORMAT(logout_time, \'%Y-%m-%d %H:%i:%s\') AS logout_time '
        'FROM plugin_statistic '
        'WHERE platform = %s AND user_name = %s AND login_time BETWEEN %s AND %s'
    ),
}

