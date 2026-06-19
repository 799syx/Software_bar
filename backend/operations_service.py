import time


def clamp_operation_value(value, minimum, maximum):
    return max(minimum, min(maximum, int(round(value))))


def operation_counts(connection_factory, today_ts, week_ts):
    with connection_factory() as connection:
        return {
            "questionCount": connection.execute("SELECT COUNT(*) FROM chat_record").fetchone()[0],
            "routeCount": connection.execute("SELECT COUNT(*) FROM route_record").fetchone()[0],
            "todayQuestions": connection.execute("SELECT COUNT(*) FROM chat_record WHERE created_at >= ?", (today_ts,)).fetchone()[0],
            "todayRoutes": connection.execute("SELECT COUNT(*) FROM route_record WHERE created_at >= ?", (today_ts,)).fetchone()[0],
            "weekQuestions": connection.execute("SELECT COUNT(*) FROM chat_record WHERE created_at >= ?", (week_ts,)).fetchone()[0],
            "weekRoutes": connection.execute("SELECT COUNT(*) FROM route_record WHERE created_at >= ?", (week_ts,)).fetchone()[0],
        }


def operations_overview(connection_factory, today_ts, week_ts):
    counts = operation_counts(connection_factory, today_ts, week_ts)
    question_count = counts["questionCount"]
    route_count = counts["routeCount"]
    today_service_count = counts["todayQuestions"] + counts["todayRoutes"]
    week_service_count = counts["weekQuestions"] + counts["weekRoutes"]
    base_load = max(today_service_count, question_count + route_count, 1)
    capacity_rate = clamp_operation_value(52 + (base_load % 36), 48, 92)
    passage_index = clamp_operation_value(96 - capacity_rate * 0.32, 58, 92)
    patrol_coverage = clamp_operation_value(72 + (week_service_count % 18), 68, 96)
    device_health = clamp_operation_value(94 - min(question_count % 18, 18), 76, 98)
    duty_status = "高位值守" if capacity_rate >= 86 else "需关注" if capacity_rate >= 76 else "正常"

    return {
        "available": True,
        "generatedAt": int(time.time()),
        "sourceType": "derived_from_service_records",
        "sourceDescription": "由问答记录与路线推荐记录推导的演示运营概览。",
        "core": {
            "title": "灵山胜境",
            "keyArea": "主轴线",
            "dutyStatus": duty_status,
            "summary": "以园区承载、通行动线、设备健康和现场值守为核心视角，监控景区当日运行状态。",
        },
        "metrics": [
            {"key": "capacity", "label": "园区承载", "value": capacity_rate, "unit": "%", "detail": "主游线当前负载"},
            {"key": "passage", "label": "通行指数", "value": passage_index, "unit": "分", "detail": "入口与主轴线顺畅度"},
            {"key": "patrol", "label": "巡检覆盖", "value": patrol_coverage, "unit": "%", "detail": "重点片区巡检完成度"},
            {"key": "device", "label": "设备健康", "value": device_health, "unit": "%", "detail": "闸机、屏显与广播状态"},
        ],
        "stations": [
            {"key": "north_gate", "name": "北入口", "role": "入园通行", "status": f"负载 {capacity_rate}%", "value": capacity_rate},
            {"key": "main_axis", "name": "主轴线", "role": "客流疏导", "status": f"通行 {passage_index} 分", "value": passage_index},
            {"key": "service_center", "name": "服务中心", "role": "现场值守", "status": f"巡检 {patrol_coverage}%", "value": patrol_coverage},
        ],
        "resources": [
            {"key": "gate", "label": "闸机状态", "value": f"{passage_index}%", "detail": "入口通行能力保持稳定"},
            {"key": "broadcast", "label": "广播联动", "value": "正常", "detail": "服务中心与主轴线可联动播报"},
            {"key": "emergency", "label": "应急值守", "value": duty_status, "detail": "高峰片区保留机动处置能力"},
        ],
        "flow": [
            {"label": "入口", "value": capacity_rate},
            {"label": "主轴", "value": passage_index},
            {"label": "巡检", "value": patrol_coverage},
            {"label": "设备", "value": device_health},
            {"label": "出口", "value": max(56, 100 - capacity_rate + 38)},
        ],
        "trend": [
            {"label": "08:00", "value": max(42, capacity_rate - 18)},
            {"label": "10:00", "value": max(48, capacity_rate - 6)},
            {"label": "12:00", "value": capacity_rate},
            {"label": "14:00", "value": min(96, capacity_rate + 8)},
            {"label": "16:00", "value": max(52, capacity_rate - 10)},
        ],
        "briefings": [
            {"intent": "入口", "value": f"{passage_index}分", "message": "北入口闸机与安检口保持顺畅"},
            {"intent": "主游线", "value": f"{capacity_rate}%", "message": "主轴线客流进入可控高位"},
            {"intent": "巡检", "value": f"{patrol_coverage}%", "message": "核心片区巡检任务按计划推进"},
            {"intent": "设备", "value": f"{device_health}%", "message": "广播、屏显、应急联动链路正常"},
        ],
        "dataSource": {
            "method": "derived_operations_v1",
            "service": "chat_record / route_record",
            "questionCount": question_count,
            "routeCount": route_count,
            "todayServiceCount": today_service_count,
            "weekServiceCount": week_service_count,
        },
    }
