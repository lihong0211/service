# service/en_desktop/avatar.py
"""
en-desktop 用户头像：小程序 chooseAvatar 选取后的临时文件在这里落盘。
跟 sentences.py 的例句音频一样，存本地 static 目录 + 拼公网 URL，同一套环境变量风格，
不引入新的对象存储依赖。
"""
import os
import uuid

from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopUser

STATIC_DIR = os.environ.get("AVATAR_STATIC_DIR", "/lihong/static/en_desktop_avatars")
PUBLIC_BASE_URL = os.environ.get(
    "AVATAR_PUBLIC_BASE_URL", "https://doctor-dog.com/static/en_desktop_avatars"
)


def save_avatar(user_id: int, content: bytes) -> dict:
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
        filename = f"{user_id}_{uuid.uuid4().hex}.jpg"
        with open(os.path.join(STATIC_DIR, filename), "wb") as f:
            f.write(content)

        avatar_url = f"{PUBLIC_BASE_URL}/{filename}"
        EnDesktopUser.update({"id": user_id, "avatar": avatar_url})
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopUser.get_by_id(user_id).public_dict(),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)
