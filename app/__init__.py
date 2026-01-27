# app/__init__.py
"""
应用初始化模块
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config.db import DB_CONFIG, DB_PDD_CONFIG

db = SQLAlchemy()
pdd_db = SQLAlchemy()


def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 配置主数据库
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        f"?charset={DB_CONFIG.get('charset', 'utf8mb4')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    
    # 初始化主数据库
    db.init_app(app)
    
    # 配置PDD数据库（如果需要使用绑定）
    app.config['SQLALCHEMY_BINDS'] = {
        'pdd': (
            f"mysql+pymysql://{DB_PDD_CONFIG['user']}:{DB_PDD_CONFIG['password']}"
            f"@{DB_PDD_CONFIG['host']}:{DB_PDD_CONFIG['port']}/{DB_PDD_CONFIG['database']}"
            f"?charset={DB_PDD_CONFIG.get('charset', 'utf8mb4')}"
        )
    }
    
    return app


