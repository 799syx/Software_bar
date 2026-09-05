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


def percent_number(value, total):
    if not total:
        return 0
    return int(round((float(value or 0) / max(float(total or 0), 1.0)) * 100))


def behavior_operations_overview(behavior):
    row_count = int(behavior.get("rowCount") or behavior.get("behaviorRecordCount") or 0)
    if not behavior.get("available") or not row_count:
        return None

    average_satisfaction = float(behavior.get("averageSatisfaction") or 0)
    satisfaction_index = clamp_operation_value((average_satisfaction / 5) * 100, 0, 100)
    matched_rows = int(behavior.get("matchedScenicRows") or row_count)
    average_stay = float(behavior.get("averageStayDuration") or 0)
    average_group = float(behavior.get("averageGroupSize") or 0)
    top_attractions = behavior.get("topAttractions") or []
    type_distribution = behavior.get("typeDistribution") or []
    satisfaction_trend = behavior.get("satisfactionTrend") or []
    consumption = behavior.get("consumptionBreakdown") or []
    latest_trend = satisfaction_trend[-1] if satisfaction_trend else {}
    latest_count = int(latest_trend.get("count") or 0)
    max_month_count = max([int(item.get("count") or 0) for item in satisfaction_trend] + [latest_count, 1])
    latest_load = clamp_operation_value(percent_number(latest_count, max_month_count), 0, 100)
    top_name = top_attractions[0][0] if top_attractions else "暂无热点"
    source = behavior.get("dataSource") or {}

    return {
        "available": True,
        "generatedAt": int(time.time()),
        "sourceType": "behavior_visit_record",
        "sourceDescription": "由 behavior_visit_record 数据库表聚合，上传新的行为 Excel 后自动更新。",
        "core": {
            "title": "游客行为数据库",
            "keyArea": str(top_name),
            "dutyStatus": f"已入库 {row_count:,} 条",
            "summary": f"当前大屏基于 {row_count:,} 条灵山游客行为记录，平均满意度 {average_satisfaction:.2f}/5.0，覆盖停留、消费、客群与景区偏好分析。",
        },
        "metrics": [
            {"key": "sample", "label": "灵山记录", "value": row_count, "unit": "条", "detail": "已筛选灵山相关游客行为明细"},
            {"key": "satisfaction", "label": "满意指数", "value": satisfaction_index, "unit": "分", "detail": f"{average_satisfaction:.2f}/5.0 平均满意度"},
            {"key": "stay", "label": "平均停留", "value": average_stay, "unit": "小时", "detail": "灵山游客平均停留时长"},
            {"key": "matched", "label": "筛选记录", "value": matched_rows, "unit": "条", "detail": "命中灵山、拈花湾或灵山大佛"},
        ],
        "stations": [
            {
                "key": f"hot_{index}",
                "name": str(name),
                "role": "热门景区",
                "status": f"{int(count):,} 条记录",
                "value": int(count),
            }
            for index, (name, count) in enumerate(top_attractions[:3])
        ],
        "resources": [
            {
                "key": f"spend_{index}",
                "label": str(item.get("name") or "消费"),
                "value": f"{float(item.get('value') or 0):.2f}",
                "detail": "人均消费字段均值",
            }
            for index, item in enumerate(consumption[:5])
        ],
        "flow": [
            {"label": str(name), "value": int(count)}
            for name, count in type_distribution[:5]
        ],
        "trend": [
            {"label": str(item.get("date") or ""), "value": clamp_operation_value((float(item.get("score") or 0) / 5) * 100, 0, 100)}
            for item in satisfaction_trend[-6:]
        ],
        "briefings": [
            {"intent": "数据源", "value": str(source.get("file") or behavior.get("sampleSourceFile") or ""), "message": "当前大屏使用已入库行为数据"},
            {"intent": "样本量", "value": f"{row_count:,}条", "message": "上传新 Excel 后会全量替换数据库行为明细"},
            {"intent": "满意度", "value": f"{average_satisfaction:.2f}分", "message": "来自 satisfaction 字段聚合"},
            {"intent": "停留", "value": f"{average_stay:.2f}小时", "message": f"平均同行人数 {average_group:.2f} 人"},
            {"intent": "热度", "value": f"{latest_load}%", "message": "按最近月份样本量折算"},
        ],
        "dataSource": {
            "method": "behavior_visit_record_v1",
            "table": "behavior_visit_record",
            "sourceFile": source.get("file") or behavior.get("sampleSourceFile") or "",
            "rowCount": row_count,
            "matchedScenicRows": matched_rows,
        },
    }


def operations_overview(connection_factory, today_ts, week_ts, behavior=None):
    behavior_overview = behavior_operations_overview(behavior or {})
    if behavior_overview:
        return behavior_overview

    counts = operation_counts(connection_factory, today_ts, week_ts)
    question_count = counts["questionCount"]
    route_count = counts["routeCount"]
    today_service_count = counts["todayQuestions"] + counts["todayRoutes"]
    week_service_count = counts["weekQuestions"] + counts["weekRoutes"]
    total_service_count = question_count + route_count
    duty_status = "有新增服务" if today_service_count else "暂无今日新增"

    return {
        "available": True,
        "generatedAt": int(time.time()),
        "sourceType": "service_records",
        "sourceDescription": "由 chat_record 与 route_record 数据库表聚合的服务运营概览。",
        "core": {
            "title": "数字人服务记录",
            "keyArea": "问答 / 路线",
            "dutyStatus": duty_status,
            "summary": f"当前运营概览基于 {question_count:,} 条问答记录与 {route_count:,} 条路线记录聚合；未接入现场客流、设备或巡检传感器时，不生成现场状态估算。",
        },
        "metrics": [
            {"key": "questions", "label": "问答记录", "value": question_count, "unit": "条", "detail": "chat_record 表累计记录"},
            {"key": "routes", "label": "路线记录", "value": route_count, "unit": "条", "detail": "route_record 表累计记录"},
            {"key": "today", "label": "今日服务", "value": today_service_count, "unit": "次", "detail": "今日问答与路线生成合计"},
            {"key": "week", "label": "本周服务", "value": week_service_count, "unit": "次", "detail": "本周问答与路线生成合计"},
        ],
        "stations": [
            {"key": "qa", "name": "数字人问答", "role": "游客咨询", "status": f"{question_count:,} 条记录", "value": question_count},
            {"key": "route", "name": "路线推荐", "role": "个性化游线", "status": f"{route_count:,} 条记录", "value": route_count},
            {"key": "today", "name": "今日服务", "role": "当日触达", "status": f"{today_service_count:,} 次", "value": today_service_count},
        ],
        "resources": [
            {"key": "chat", "label": "问答表", "value": f"{question_count:,}", "detail": "chat_record 后端接口聚合"},
            {"key": "route", "label": "路线表", "value": f"{route_count:,}", "detail": "route_record 后端接口聚合"},
            {"key": "service", "label": "服务合计", "value": f"{total_service_count:,}", "detail": "问答与路线记录合计"},
        ],
        "flow": [
            {"label": "问答", "value": question_count},
            {"label": "路线", "value": route_count},
            {"label": "今日", "value": today_service_count},
            {"label": "本周", "value": week_service_count},
        ],
        "trend": [
            {"label": "问答", "value": question_count},
            {"label": "路线", "value": route_count},
            {"label": "今日", "value": today_service_count},
            {"label": "本周", "value": week_service_count},
        ],
        "briefings": [
            {"intent": "问答", "value": f"{question_count:,}条", "message": "来自 chat_record 表的真实问答记录"},
            {"intent": "路线", "value": f"{route_count:,}条", "message": "来自 route_record 表的真实路线生成记录"},
            {"intent": "今日", "value": f"{today_service_count:,}次", "message": "按 created_at 统计今日服务记录"},
            {"intent": "本周", "value": f"{week_service_count:,}次", "message": "按 created_at 统计本周服务记录"},
        ],
        "dataSource": {
            "method": "service_records_v1",
            "service": "chat_record / route_record",
            "questionCount": question_count,
            "routeCount": route_count,
            "todayServiceCount": today_service_count,
            "weekServiceCount": week_service_count,
        },
    }
