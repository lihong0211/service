# service/en_desktop/daily_expressions.py
"""
en-desktop 日常用语服务：CRUD + 分页列表
"""
from app.database import db
from app.errors import unexpected_error_response
from model.en_desktop import EnDesktopDailyExpression


def list_expressions(page: int = 1, page_size: int = 10, search: str | None = None) -> dict:
    try:
        query = db.session.query(EnDesktopDailyExpression).where(
            EnDesktopDailyExpression.deleted_at.is_(None)
        )
        if search:
            query = query.where(EnDesktopDailyExpression.phrase.like(f"%{search.strip()}%"))
        total = query.count()
        rows = (
            query.order_by(EnDesktopDailyExpression.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "list": [r.to_dict() for r in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def get_expression(expression_id: int) -> dict:
    try:
        row = EnDesktopDailyExpression.get_by_id(expression_id)
        if not row:
            return {"code": 500, "msg": "记录不存在"}
        return {"code": 200, "msg": "success", "data": row.to_dict()}
    except Exception as e:
        return unexpected_error_response(e, db.session)


def add_expression(data: dict) -> dict:
    phrase = (data.get("phrase") or "").strip()
    meaning = (data.get("meaning") or "").strip()
    if not phrase or not meaning:
        return {"code": 400, "msg": "phrase / meaning 不能为空"}

    try:
        expression_id = EnDesktopDailyExpression.insert({"phrase": phrase, "meaning": meaning})
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopDailyExpression.get_by_id(expression_id).to_dict(),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def update_expression(expression_id: int, data: dict) -> dict:
    try:
        existing = EnDesktopDailyExpression.get_by_id(expression_id)
        if not existing:
            return {"code": 500, "msg": "记录不存在"}

        update_dict = {"id": expression_id}
        if data.get("phrase") is not None:
            update_dict["phrase"] = data["phrase"].strip()
        if data.get("meaning") is not None:
            update_dict["meaning"] = data["meaning"].strip()
        EnDesktopDailyExpression.update(update_dict)
        return {
            "code": 200,
            "msg": "success",
            "data": EnDesktopDailyExpression.get_by_id(expression_id).to_dict(),
        }
    except Exception as e:
        return unexpected_error_response(e, db.session)


def delete_expression(expression_id: int) -> dict:
    try:
        EnDesktopDailyExpression.delete(expression_id)
        return {"code": 200, "msg": "success", "data": None}
    except Exception as e:
        return unexpected_error_response(e, db.session)
