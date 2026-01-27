# service/peach/pluginStatistic/__init__.py
"""
插件统计服务模块 - 使用ORM
"""
from datetime import datetime
from flask import request, jsonify
from app.app import db
from model.peach import PluginStatistic, Version
from sqlalchemy import func, text


def add():
    """增加插件统计"""
    data = request.get_json()
    userName = data.get("userName")
    platform = data.get("platform")
    pluginVersion = data.get("pluginVersion")
    status = data.get("status")

    try:
        # 更新登出时间（将在线状态更新为离线）
        PluginStatistic.batch_update(
            {"user_name": userName, "status": "online"},
            {"logout_time": datetime.now(), "status": "offline"},
        )

        if status == "offline":
            return jsonify({"code": 200, "msg": "success"})

        # 添加版本信息
        existing_version = Version.query.filter(
            Version.name == userName, Version.platform == platform, Version.deleted_at.is_(None)
        ).first()

        if existing_version:
            Version.update({"id": existing_version.id, "version": pluginVersion})
        else:
            Version.insert({"version": pluginVersion, "name": userName, "platform": platform})

        # 如果是在线状态，插入统计记录
        if status == "online":
            PluginStatistic.insert(
                {
                    "user_name": userName,
                    "platform": platform,
                    "plugin_version": pluginVersion,
                    "status": status,
                }
            )

        return jsonify({"code": 200, "msg": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "msg": str(e)})


def list_statistics():
    """查询插件统计列表"""
    data = request.get_json() if request.is_json else {}
    platform = data.get("platform")
    userName = data.get("userName")
    today = datetime.now().strftime("%Y-%m-%d")
    startTime = data.get("startTime", f"{today} 00:00:00")
    endTime = data.get("endTime", f"{today} 23:59:59")

    try:
        # 构建查询条件
        criterion = {
            "login_time": {"type": "bt", "start": startTime, "end": endTime},
        }
        if platform:
            criterion["platform"] = platform
        if userName:
            criterion["user_name"] = userName

        # 只查询有登出时间的记录
        query = PluginStatistic.builder_query(criterion)
        query = query.filter(PluginStatistic.logout_time.isnot(None))

        # 使用原生SQL进行分组统计（因为需要日期格式化和时间计算）
        results = (
            db.session.query(
                PluginStatistic.user_name,
                PluginStatistic.platform,
                PluginStatistic.plugin_version,
                func.DATE_FORMAT(PluginStatistic.login_time, "%Y-%m-%d").label("date"),
                func.SUM(
                    func.TIMESTAMPDIFF(
                        text("SECOND"), PluginStatistic.login_time, PluginStatistic.logout_time
                    )
                ).label("seconds"),
                func.SEC_TO_TIME(
                    func.SUM(
                        func.TIMESTAMPDIFF(
                            text("SECOND"),
                            PluginStatistic.login_time,
                            PluginStatistic.logout_time,
                        )
                    )
                ).label("hms"),
            )
            .filter(
                PluginStatistic.login_time >= startTime,
                PluginStatistic.login_time <= endTime,
                PluginStatistic.logout_time.isnot(None),
            )
        )

        if platform:
            results = results.filter(PluginStatistic.platform == platform)
        if userName:
            results = results.filter(PluginStatistic.user_name == userName)

        results = (
            results.group_by(
                func.DATE_FORMAT(PluginStatistic.login_time, "%Y-%m-%d"),
                PluginStatistic.user_name,
                PluginStatistic.platform,
                PluginStatistic.plugin_version,
            )
            .order_by("date")
            .all()
        )

        data_list = []
        for row in results:
            data_list.append(
                {
                    "user_name": row.user_name,
                    "platform": row.platform,
                    "plugin_version": row.plugin_version,
                    "date": row.date,
                    "seconds": row.seconds or 0,
                    "hms": str(row.hms) if row.hms else "00:00:00",
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


def detail():
    """查询插件统计详情"""
    data = request.get_json()
    platform = data.get("platform")
    userName = data.get("userName")
    startTime = data.get("startTime")
    endTime = data.get("endTime")

    try:
        criterion = {
            "platform": platform,
            "user_name": userName,
            "login_time": {"type": "bt", "start": startTime, "end": endTime},
        }

        results = PluginStatistic.select_by(criterion)

        data_list = []
        for item in results:
            duration_str = None
            if item.duration:
                hours = item.duration // 3600
                minutes = (item.duration % 3600) // 60
                seconds = item.duration % 60
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            data_list.append(
                {
                    "user_name": item.user_name,
                    "platform": item.platform,
                    "plugin_version": item.plugin_version,
                    "duration": duration_str,
                    "login_time": item.login_time.strftime("%Y-%m-%d %H:%M:%S")
                    if item.login_time
                    else None,
                    "logout_time": item.logout_time.strftime("%Y-%m-%d %H:%M:%S")
                    if item.logout_time
                    else None,
                }
            )

        return jsonify({"code": 200, "data": {"data": data_list}})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
