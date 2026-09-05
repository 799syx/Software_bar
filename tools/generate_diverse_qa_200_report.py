from __future__ import annotations

import importlib
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
os.chdir(ROOT)
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

app_core = importlib.import_module("backend.app_core")


def stub_generate_llm_answer(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment):
    return {
        "answer": "[LLM stub] 当前问题未由本地知识库或结构化规则直接回答，正常运行时会进入大模型分支。",
        "relatedSpots": matched_spots[:3],
        "sourceRefs": [{"type": "model", "title": "deepseek-chat", "category": "stub"}],
        "intent": intent,
        "confidence": 0.5,
        "sentiment": sentiment,
        "llmProvider": "deepseek_stub",
        "modelName": "deepseek-chat",
        "fallback": True,
    }


app_core.generate_llm_answer = stub_generate_llm_answer


def normalize(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def compact(value, limit=140):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ，。；;、") + "..."


def fragments(value, min_len=2):
    return [part.strip() for part in re.split(r"[，,。；;、\s（）()]+", str(value or "")) if len(part.strip()) >= min_len]


def numeric_or_text_fragments(value):
    text = str(value or "")
    numbers = re.findall(r"\d+(?:\.\d+)?\s*(?:米|m|㎡|吨|分钟|:|：)?", text, re.I)
    words = fragments(text, min_len=3)
    return [*numbers[:5], *words[:5]]


def case(
    category,
    question,
    expected_all=None,
    expected_any=None,
    allowed_providers=None,
    forbidden_any=None,
    note="",
    mode="fast",
):
    return {
        "category": category,
        "question": question,
        "expectedAll": expected_all or [],
        "expectedAny": expected_any or [],
        "allowedProviders": allowed_providers or [],
        "forbiddenAny": forbidden_any or [],
        "note": note,
        "mode": mode,
    }


def check_case(item, result):
    answer = result.get("answer", "")
    answer_n = normalize(answer)
    failures = []

    allowed = item.get("allowedProviders") or []
    if allowed and result.get("llmProvider") not in allowed:
        failures.append(f"来源应为 {'/'.join(allowed)}，实际 {result.get('llmProvider')}")

    for expected in item.get("expectedAll") or []:
        if normalize(expected) not in answer_n:
            failures.append(f"缺少关键词：{expected}")

    for group in item.get("expectedAny") or []:
        candidates = group if isinstance(group, (list, tuple, set)) else [group]
        if candidates and not any(normalize(candidate) in answer_n for candidate in candidates):
            failures.append(f"未命中任一关键词：{' / '.join(str(candidate) for candidate in candidates)}")

    forbidden = item.get("forbiddenAny") or []
    found_forbidden = [word for word in forbidden if normalize(word) in answer_n]
    if found_forbidden:
        failures.append(f"包含不应出现内容：{' / '.join(found_forbidden)}")

    return not failures, "；".join(failures) if failures else "通过"


def build_dynamic_cases(spots, records_by_name):
    cases = []
    active_spots = [spot for spot in spots if spot.get("status") == "active"]

    for spot in active_spots[:21]:
        location_terms = fragments(spot.get("location", ""), min_len=4)[:4]
        cases.append(
            case(
                "景点位置",
                f"{spot['name']}在哪里？",
                expected_all=[spot["name"]],
                expected_any=[location_terms] if location_terms else [],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    for spot in active_spots[:21]:
        start_terms = ["游客服务中心", "景区入口", "拈花广场", "香月花街"]
        route_terms = ["导视牌", "→", "景观栈道", "顺序走", "主游线"]
        cases.append(
            case(
                "景点问路",
                f"{spot['name']}怎么走？",
                expected_all=[spot["name"]],
                expected_any=[start_terms, route_terms],
                allowed_providers=["knowledge_base", "local_fact", "local"],
            )
        )

    for spot in active_spots[:21]:
        open_time = str(spot.get("openTime", ""))
        times = re.findall(r"\d{1,2}:\d{2}", open_time)
        open_terms = times[:3] or ["开放", "公告", "广播", "随景区开放"]
        cases.append(
            case(
                "开放时间",
                f"{spot['name']}几点开放？",
                expected_all=[spot["name"]],
                expected_any=[open_terms],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    for spot in active_spots[:21]:
        cases.append(
            case(
                "建议时长",
                f"{spot['name']}建议游览多久？",
                expected_all=[spot["name"], str(spot.get("duration", ""))],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    for spot in active_spots[:21]:
        cases.append(
            case(
                "拍照打卡",
                f"{spot['name']}适合拍照吗？",
                expected_all=["适合"],
                expected_any=[[spot["name"]]],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    parameter_spots = [spot for spot in active_spots if records_by_name.get(spot["name"], {}).get("parameters")]
    for spot in parameter_spots[:15]:
        params = numeric_or_text_fragments(records_by_name[spot["name"]].get("parameters", ""))
        cases.append(
            case(
                "建筑参数",
                f"{spot['name']}有什么建筑参数？",
                expected_all=[spot["name"]],
                expected_any=[params],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    performance_spots = [spot for spot in active_spots if records_by_name.get(spot["name"])]
    for spot in performance_spots[:15]:
        open_info = records_by_name.get(spot["name"], {}).get("openInfo", "") or spot.get("openTime", "")
        times = re.findall(r"\d{1,2}:\d{2}", open_info)
        if any(term in open_info for term in ("表演", "演出", "场次", "巡游", "灯光秀", "开园仪式")):
            expected = [*times[:4], "表演", "演出", "巡游", "场次", "广播"]
        else:
            expected = ["没有固定表演时间", "公告", "广播", "开放时间"]
        cases.append(
            case(
                "演出表演",
                f"{spot['name']}有表演时间吗？",
                expected_all=[spot["name"]],
                expected_any=[expected],
                allowed_providers=["knowledge_base", "local_fact"],
            )
        )

    return cases


def build_curated_cases():
    local_or_knowledge = ["knowledge_base", "local_fact", "local"]
    llm_or_local = ["deepseek_stub", "local_fact", "local"]
    return [
        case("路线推荐", "亲子家庭路线怎么安排？", ["九龙灌浴", "五印坛城"], [["灵山梵宫", "梵宫"]], local_or_knowledge),
        case("路线推荐", "喜欢历史文化，灵山胜境怎么逛？", ["灵山大照壁", "五印坛城"], [["祥符禅寺", "灵山大佛"]], local_or_knowledge),
        case("路线推荐", "自然风光爱好者适合什么路线？", ["佛足坛", "九龙灌浴"], [["曼飞龙塔", "菩提大道"]], local_or_knowledge),
        case("路线推荐", "哪里适合拍照打卡？", ["五印坛城"], [["灵山大照壁", "九龙灌浴", "曼飞龙塔"]], local_or_knowledge),
        case("路线推荐", "从灵山梵宫到五印坛城怎么走？", ["五印坛城"], [["景观栈道", "灵山梵宫"]], local_or_knowledge),
        case("路线推荐", "入口到灵山大佛怎么走？", ["灵山大佛"], [["游客服务中心", "灵山大照壁", "五明桥"]], local_or_knowledge),
        case("路线推荐", "带孩子先玩哪里？", [], [["九龙灌浴", "百子戏弥勒", "亲子"]], local_or_knowledge),
        case("路线推荐", "老人游览路线怎么安排更轻松？", [], [["观光车", "服务中心", "无障碍", "工作人员"]], local_or_knowledge),
        case("路线推荐", "我只有两个小时，灵山胜境怎么逛？", [], [["路线", "优先", "建议", "生成"]], local_or_knowledge),
        case("路线推荐", "想看佛教文化怎么安排？", [], [["灵山大佛", "灵山梵宫", "五印坛城"]], local_or_knowledge),
        case("票务价格", "灵山胜境成人票多少钱？", ["210"], [["成人票", "门票"]], local_or_knowledge),
        case("票务价格", "半价票多少钱，哪些人能买？", ["105"], [["6-18", "60-69", "半价"]], local_or_knowledge),
        case("票务价格", "哪些游客可以免票？", [], [["70周岁", "现役军人", "残疾人", "1.4米"]], local_or_knowledge),
        case("票务价格", "门票加观光车联票多少钱？", ["225"], [["观光车", "联票"]], local_or_knowledge),
        case("票务价格", "观光车单独购票多少钱？", ["40"], [["观光车"]], local_or_knowledge),
        case("交通服务", "停车场在哪里？", [], [["停车", "现场指引", "服务中心"]], local_or_knowledge),
        case("交通服务", "游客服务中心在哪里？", ["游客服务中心"], [["景区入口", "入口服务区"]], local_or_knowledge),
        case("交通服务", "观光车怎么坐？", [], [["观光车", "换乘", "体力"]], local_or_knowledge),
        case("安全服务", "我在景区迷路了怎么办？", [], [["游客服务中心", "工作人员", "现场"]], local_or_knowledge),
        case("安全服务", "身体不舒服应该去哪里？", [], [["服务中心", "工作人员", "急救", "医药箱"]], local_or_knowledge),
        case("安全服务", "东西丢了怎么办？", [], [["失物招领", "服务中心", "工作人员"]], local_or_knowledge),
        case("安全服务", "行动不便游客怎么办？", [], [["轮椅", "无障碍", "观光车", "服务中心"]], local_or_knowledge),
        case("游览贴士", "游览灵山胜境穿什么比较合适？", [], [["运动鞋", "防晒", "雨伞", "充电宝"]], local_or_knowledge),
        case("游览贴士", "什么时候去灵山胜境比较合适？", [], [["春秋", "9点前", "太湖日落"]], local_or_knowledge),
        case("餐饮购物", "景区里有什么素食推荐？", [], [["梵宫素斋", "素面", "灵山精舍"]], local_or_knowledge),
        case("文化礼仪", "在佛教文化场所游览要注意什么？", [], [["保持安静", "尊重宗教", "不触摸佛像"]], local_or_knowledge),
        case("文化讲解", "灵山大佛手印有什么含义？", [], [["无畏印", "与愿印", "痛苦", "欢乐"]], local_or_knowledge),
        case("文化讲解", "216级登云道有什么寓意？", ["216"], [["108烦恼", "108愿望"]], local_or_knowledge),
        case("文化讲解", "五明桥代表什么？", [], [["声明", "因明", "内明", "医方明", "工巧明"]], local_or_knowledge),
        case("文化讲解", "百子戏弥勒适合亲子游吗？", [], [["百名孩童", "多子多福", "亲子"]], local_or_knowledge),
        case("闲聊通用", "你好", [], [["你好"]], llm_or_local),
        case("闲聊通用", "谢谢你", [], [["不客气", "LLM stub"]], llm_or_local),
        case("闲聊通用", "你是谁？", [], [["数字导览助手", "LLM stub"]], llm_or_local),
        case("闲聊通用", "现在几点？", [], [[":", "："]], llm_or_local),
        case("非景区问题", "Python 怎么读取 JSON 文件？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "帮我翻译 hello world", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "番茄炒蛋怎么做？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "什么是数据库索引？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "怎么写单元测试？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "帮我写一句晚安", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("实时信息", "今天适合带伞吗？", [], [["LLM stub", "天气"]], llm_or_local, mode="normal"),
        case("实时信息", "美元兑人民币现在多少？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("旅行泛问", "杭州有什么好吃的？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("设备求助", "手机没电了怎么办？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("隐私安全", "怎么识别诈骗电话？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("演出表演", "九龙灌浴平日表演时间是什么时候？", ["10:00", "11:30", "13:30", "15:00"], [], local_or_knowledge),
        case("演出表演", "梵宫《吉祥颂》演出时间？", ["10:35", "11:30", "14:00", "16:00"], [["20分钟"]], local_or_knowledge),
        case("文化体验", "五印坛城有什么互动体验？", [], [["绕坛城", "转动转经筒", "藏香"]], local_or_knowledge),
        case("文化讲解", "灵山梵宫为什么重要？", [], [["世界佛教论坛", "佛教艺术殿堂", "木雕", "壁画", "琉璃"]], local_or_knowledge),
        case("文化讲解", "祥符禅寺有什么历史？", [], [["唐代", "北宋大中祥符", "千年古刹"]], local_or_knowledge),
        case("文化讲解", "灵山大照壁有什么特色？", [], [["39.8米", "7米", "赵朴初", "华夏第一壁"]], local_or_knowledge),
        case("文化讲解", "灵山大佛有多高？", ["88"], [["101.5", "725吨"]], local_or_knowledge),
        case("服务咨询", "景区厕所在哪里？", [], [["卫生间", "厕所", "服务中心", "导视"]], local_or_knowledge),
        case("服务咨询", "有母婴室吗？", [], [["母婴", "服务中心", "现场"]], local_or_knowledge),
        case("服务咨询", "可以寄存行李吗？", [], [["寄存", "服务中心", "现场"]], local_or_knowledge),
        case("路线推荐", "想少走路可以坐观光车吗？", [], [["观光车", "体力", "老人儿童", "换乘"]], local_or_knowledge),
        case("安全服务", "下雨天登云道要注意什么？", [], [["防滑", "台阶", "雨天", "体力"]], local_or_knowledge),
        case("拍照打卡", "五印坛城适合拍什么？", ["五印坛城"], [["建筑", "环境", "拍照", "打卡"]], local_or_knowledge),
        case("拍照打卡", "灵山大佛哪里拍照好看？", ["灵山大佛"], [["地标", "佛脚", "太湖", "夕阳", "拍"]], local_or_knowledge),
        case("口语问法", "大佛多高啊？", ["88"], [["101.5", "725吨"]], local_or_knowledge),
        case("口语问法", "梵宫几点有演出？", [], [["10:35", "11:30", "14:00", "16:00"]], local_or_knowledge),
        case("口语问法", "坛城咋过去？", [], [["五印坛城", "景观栈道", "灵山梵宫", "导视牌"]], local_or_knowledge),
        case("口语问法", "我想买观光车票，多少钱？", ["40"], [["观光车"]], local_or_knowledge),
        case("非景区问题", "HTTP 和 HTTPS 有什么区别？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "Docker 是做什么的？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "Excel 怎么冻结首行？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "怎么提高睡眠质量？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "飞机延误怎么办？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("非景区问题", "酒店入住需要什么证件？", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
        case("闲聊通用", "讲个笑话", [], [["LLM stub"]], ["deepseek_stub"], mode="normal"),
    ]


def build_cases():
    spots = app_core.get_spots()
    records = app_core.parse_official_spot_records()
    records_by_name = {record["name"]: record for record in records}
    cases = [*build_dynamic_cases(spots, records_by_name), *build_curated_cases()]
    if len(cases) < 200:
        raise RuntimeError(f"测试题不足 200 条，当前 {len(cases)} 条")
    return cases[:200]


def run_cases(cases):
    rows = []
    for index, item in enumerate(cases, 1):
        os.environ["SCENIC_CHAT_FAST_MODE"] = "true" if item.get("mode") == "fast" else "false"
        started = time.perf_counter()
        result = app_core.answer_question(item["question"])
        latency_ms = int((time.perf_counter() - started) * 1000)
        passed, message = check_case(item, result)
        refs = result.get("sourceRefs") or []
        source = refs[0].get("title", "-") if refs else "-"
        row = {
            "index": index,
            "category": item["category"],
            "question": item["question"],
            "answer": result.get("answer", ""),
            "provider": result.get("llmProvider", ""),
            "intent": result.get("intent", ""),
            "confidence": result.get("confidence", ""),
            "source": source,
            "latencyMs": latency_ms,
            "passed": passed,
            "message": message,
            "note": item.get("note", ""),
            "mode": item.get("mode", "fast"),
        }
        rows.append(row)
        if index % 25 == 0:
            print(json.dumps({"progress": index, "total": len(cases)}, ensure_ascii=False))
    return rows


def build_report(rows):
    failures = [row for row in rows if not row["passed"]]
    category_counts = Counter(row["category"] for row in rows)
    category_failures = Counter(row["category"] for row in failures)
    provider_counts = Counter(row["provider"] for row in rows)
    intent_counts = Counter(row["intent"] for row in rows)
    average_latency = round(sum(row["latencyMs"] for row in rows) / max(1, len(rows)), 1)

    lines = [
        "# 200 条多类型问答回归测试报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 测试方法",
        "",
        "- 调用入口：`backend.app_core.answer_question(question)`。",
        "- 覆盖类型：景点位置、景点问路、开放时间、建议时长、拍照打卡、建筑参数、演出表演、路线推荐、票务价格、交通服务、安全服务、游览贴士、餐饮购物、文化讲解、闲聊通用、非景区问题、实时信息。",
        "- 景区事实题使用 fast mode 测本地知识库/结构化规则；非景区题使用 normal mode，并把大模型分支替换为 `deepseek_stub`，只验证是否正确进入大模型分支。",
        "- 判定方式：检查回答来源和关键事实关键词；不是人工语义评分。",
        "",
        "## 总结",
        "",
        f"- 总题数：{len(rows)}",
        f"- 通过：{len(rows) - len(failures)}",
        f"- 未通过：{len(failures)}",
        f"- 通过率：{(len(rows) - len(failures)) / max(1, len(rows)):.1%}",
        f"- 平均耗时：{average_latency} ms",
        "",
        "### 类型统计",
        "",
        "| 类型 | 数量 | 未通过 |",
        "| --- | ---: | ---: |",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} | {category_failures.get(category, 0)} |")

    lines.extend(["", "### 来源统计", "", "| 来源 | 数量 |", "| --- | ---: |"])
    for provider, count in sorted(provider_counts.items()):
        lines.append(f"| {provider or '-'} | {count} |")

    lines.extend(["", "### 意图统计", "", "| 意图 | 数量 |", "| --- | ---: |"])
    for intent, count in sorted(intent_counts.items()):
        lines.append(f"| {intent or '-'} | {count} |")

    lines.extend(["", "## 未通过条目", ""])
    if failures:
        lines.extend(["| 序号 | 类型 | 问题 | 来源 | 回答 | 未通过原因 |", "| ---: | --- | --- | --- | --- | --- |"])
        for row in failures:
            lines.append(
                f"| {row['index']} | {row['category']} | {row['question']} | {row['provider']} | "
                f"{compact(row['answer'], 100)} | {row['message']} |"
            )
    else:
        lines.append("本次 200 题全部通过。")

    lines.extend(["", "## 明细", ""])
    lines.extend(["| 序号 | 类型 | 模式 | 问题 | 意图 | 来源 | 回答 | 耗时ms | 结果 |", "| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |"])
    for row in rows:
        status = "通过" if row["passed"] else "未通过"
        lines.append(
            f"| {row['index']} | {row['category']} | {row['mode']} | {row['question']} | {row['intent']} | {row['provider']} | "
            f"{compact(row['answer'], 120)} | {row['latencyMs']} | {status} |"
        )
    return "\n".join(lines)


def main():
    app_core.init_database()
    cases = build_cases()
    rows = run_cases(cases)
    output_path = ROOT / "docs" / "diverse_qa_200_report.md"
    output_path.write_text(build_report(rows), encoding="utf-8")
    failures = [row for row in rows if not row["passed"]]
    print(
        json.dumps(
            {
                "output": str(output_path),
                "total": len(rows),
                "passed": len(rows) - len(failures),
                "failed": len(failures),
                "passRate": round((len(rows) - len(failures)) / max(1, len(rows)), 4),
                "categoryFailures": dict(Counter(row["category"] for row in failures)),
                "providerCounts": dict(Counter(row["provider"] for row in rows)),
                "failedQuestions": [row["question"] for row in failures[:30]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
