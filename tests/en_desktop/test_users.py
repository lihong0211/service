"""
en-desktop 用户管理服务测试
"""
from model.en_desktop import EnDesktopUser
from service.en_desktop import users
from service.en_desktop.security import verify_password


def test_add_user_hashes_password(en_desktop_db):
    result = users.add_user({"username": "alice", "password": "secret"})
    assert result["code"] == 200
    assert "password" not in result["data"]

    stored = EnDesktopUser.select_one_by({"username": "alice"})
    assert stored.password != "secret"
    assert verify_password("secret", stored.password)


def test_add_user_duplicate(en_desktop_db):
    users.add_user({"username": "alice", "password": "secret"})
    result = users.add_user({"username": "alice", "password": "other"})
    assert result["code"] == 500


def test_list_users_filter_active(en_desktop_db):
    users.add_user({"username": "a1", "password": "secret", "active": 1})
    users.add_user({"username": "a2", "password": "secret", "active": 1})
    id3 = users.add_user({"username": "a3", "password": "secret"})["data"]["id"]
    users.activate_user(id3, False)

    all_users = users.list_users()
    assert len(all_users["data"]) == 3
    active_only = users.list_users(active=True)
    assert len(active_only["data"]) == 2
    inactive = users.list_users(active=False)
    assert [u["username"] for u in inactive["data"]] == ["a3"]


def test_update_user(en_desktop_db):
    user_id = users.add_user({"username": "alice", "password": "secret"})["data"]["id"]

    result = users.update_user(user_id, {"description": "hello", "password": "newpass"})
    assert result["code"] == 200
    assert result["data"]["description"] == "hello"
    stored = EnDesktopUser.get_by_id(user_id)
    assert verify_password("newpass", stored.password)

    users.add_user({"username": "bob", "password": "secret"})
    conflict = users.update_user(user_id, {"username": "bob"})
    assert conflict["code"] == 500

    assert users.update_user(9999, {"description": "x"})["code"] == 500


def test_delete_user_soft(en_desktop_db):
    user_id = users.add_user({"username": "alice", "password": "secret"})["data"]["id"]
    assert users.delete_user(user_id)["code"] == 200
    assert users.get_user(user_id)["code"] == 500
