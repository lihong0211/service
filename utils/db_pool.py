# utils/db_pool.py
"""
数据库连接池工具
"""
import sys
import os
import pymysql
from pymysql.cursors import DictCursor

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db import DB_CONFIG, DB_PDD_CONFIG


class DatabasePool:
    """数据库连接池类"""
    
    def __init__(self, config):
        self.config = config
        self.pool = None
    
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.config['host'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            port=self.config['port'],
            charset=self.config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor,
            autocommit=self.config.get('autocommit', True)
        )
    
    def execute_query(self, sql, params=None):
        """执行查询"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        finally:
            conn.close()
    
    def execute_update(self, sql, params=None):
        """执行更新"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


# 创建默认数据库连接池
db_pool = DatabasePool(DB_CONFIG)
pdd_db_pool = DatabasePool(DB_PDD_CONFIG)

