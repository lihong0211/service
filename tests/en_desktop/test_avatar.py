"""
头像保存测试：STATIC_DIR/PUBLIC_BASE_URL 走环境变量注入，测试里用 monkeypatch 指到
tmp_path，跟 sentences.py 音频文件的测试思路一致——不依赖真实服务器磁盘路径。
"""
import os

from model.en_desktop import EnDesktopUser
from service.en_desktop import auth, avatar


def test_save_avatar_writes_file_and_updates_user(en_desktop_db, tmp_path, monkeypatch):
    monkeypatch.setattr(avatar, "STATIC_DIR", str(tmp_path))
    monkeypatch.setattr(avatar, "PUBLIC_BASE_URL", "https://x.test/avatars")

    result = auth.register({"username": "alice", "password": "secret"})
    user_id = result["data"]["user"]["id"]

    saved = avatar.save_avatar(user_id, b"fake-jpg-bytes")
    assert saved["code"] == 200
    avatar_url = saved["data"]["avatar"]
    assert avatar_url.startswith("https://x.test/avatars/")

    filename = avatar_url.rsplit("/", 1)[-1]
    assert filename.startswith(f"{user_id}_")
    assert os.path.exists(os.path.join(str(tmp_path), filename))

    user = EnDesktopUser.get_by_id(user_id)
    assert user.avatar == avatar_url
