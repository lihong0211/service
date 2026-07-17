# service/en_desktop/users.py
"""
en-desktop 用户管理服务（CRUD + 激活/禁用）
"""
from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopUser
from service.en_desktop.security import hash_password


def list_users(page: int = 1, page_size: int = 10, active: bool | None = None) -> dict:
    try:
        criterion = {}
        if active is not None:
            criterion["active"] = int(active)
        users = EnDesktopUser.select_by(criterion)

        start = (page - 1) * page_size
        end = start + page_size
        return {
            "code": 200,
            "msg": "success",
            "data": [u.public_dict() for u in users[start:end]],
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get_user(user_id: int) -> dict:
    try:
        user = EnDesktopUser.get_by_id(user_id)
        if not user:
            return {"code": 500, "msg": "User not found"}
        return {"code": 200, "msg": "success", "data": user.public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_user(data: dict) -> dict:
    try:
        username = data.get("username")
        if username and EnDesktopUser.select_one_by({"username": username}):
            return {"code": 500, "msg": "Username already exists"}

        user_data = {
            key: data.get(key)
            for key in ("username", "password", "wx", "description", "active")
        }
        if user_data.get("password"):
            user_data["password"] = hash_password(user_data["password"])
        user_id = EnDesktopUser.insert(user_data)
        return {"code": 200, "msg": "success", "data": EnDesktopUser.get_by_id(user_id).public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_user(user_id: int, data: dict) -> dict:
    try:
        existing = EnDesktopUser.get_by_id(user_id)
        if not existing:
            return {"code": 500, "msg": "User not found"}

        update_dict = {
            key: data[key]
            for key in ("username", "password", "wx", "description", "active")
            if key in data and data[key] is not None
        }
        if update_dict.get("password"):
            update_dict["password"] = hash_password(update_dict["password"])

        new_username = update_dict.get("username")
        if new_username and new_username != existing.username:
            dup = EnDesktopUser.select_one_by({"username": new_username})
            if dup and dup.id != user_id:
                return {"code": 500, "msg": "Username already exists"}

        update_dict["id"] = user_id
        EnDesktopUser.update(update_dict)
        return {"code": 200, "msg": "success", "data": EnDesktopUser.get_by_id(user_id).public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_user(user_id: int) -> dict:
    try:
        EnDesktopUser.delete(user_id)
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def activate_user(user_id: int, active: bool) -> dict:
    try:
        existing = EnDesktopUser.get_by_id(user_id)
        if not existing:
            return {"code": 500, "msg": "User not found"}

        EnDesktopUser.update({"id": user_id, "active": int(active)})
        return {"code": 200, "msg": "success", "data": EnDesktopUser.get_by_id(user_id).public_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)
