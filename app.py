# app.py
"""
主应用文件
"""
from flask import Flask, jsonify
from app.app import app, db
from routes import api_bp
from model import Words, Root, Affix, Dialogue, LivingSpeech
from model.peach import (
    Chat,
    Rp,
    Manual,
    Version,
    AliRpCheck,
    PluginStatistic,
    CheckReport,
    Config,
)

# 注册蓝图
app.register_blueprint(api_bp)

# 初始化数据库表
with app.app_context():
    db.create_all()


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return (
        jsonify(
            {
                "code": 404,
                "msg": "Not Found",
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    return (
        jsonify(
            {
                "code": 500,
                "msg": "Internal Server Error",
            }
        ),
        500,
    )


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
