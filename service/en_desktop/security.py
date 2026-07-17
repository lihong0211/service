# service/en_desktop/security.py
"""
密码哈希与登录令牌
"""
import secrets

import bcrypt


def hash_password(raw: str) -> str:
    """bcrypt 哈希密码，返回可直接存库的字符串"""
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    """校验明文密码是否匹配哈希值"""
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))


def generate_token() -> str:
    """生成随机登录令牌"""
    return secrets.token_hex(32)
