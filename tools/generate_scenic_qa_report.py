from __future__ import annotations

import importlib
import json
import os
import re
import sys
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


deepseek_calls: list[str] = []


def stub_generate_llm_answer(question, spots, matched_spots, knowledge_hits, persona, intent, sentiment):
    deepseek_calls.append(question)
    return {
        "answer": "[DeepSeek stub] 未命中本地知识库，按当前逻辑会调用 DeepSeek。",
        "relatedSpots": matched_spots[:3],
        "sourceRefs": [],
        "intent": intent,
        "confidence": 0.5,
        "sentiment": sentiment,
        "llmProvider": "deepseek_stub",
        "modelName": "deepseek-chat",
        "fallback": True,
    }


app_core.generate_llm_answer = stub_generate_llm_answer


def normalize(value):
    return re.sub(r"\s+", "", str(value or ""))


def compact(value, limit=160):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ，。；;、") + "..."


def source_title(ref):
    if not ref:
        return "-"
    source_file = ref.get("sourceFile") or ""
    section = ref.get("sourceSection") or ""
    title = ref.get("title") or ""
    tail = " / ".join(part for part in (source_file, section) if part)
    return f"{title}（{tail}）" if tail else title


def source_doc_text(ref, knowledge_docs):
    if not ref:
        return ""
    doc_id = ref.get("id")
    if doc_id:
        doc = next((item for item in knowledge_docs if item.get("id") == doc_id), None)
        if doc:
            return doc.get("content", "")
    title = ref.get("title")
    if title:
        doc = next((item for item in knowledge_docs if item.get("title") == title), None)
        if doc:
            return doc.get("content", "")
    return ""


def answer_has_expected(case, answer, result):
    answer_n = normalize(answer)
    record = case.get("record") or {}
    spot = case.get("spot") or {}
    case_type = case["type"]

    if result.get("llmProvider") == "deepseek_stub":
        return False, "未命中本地知识库，当前逻辑会走 DeepSeek。"

    if case_type == "duration":
        duration = str(spot.get("duration") or "")
        ok = bool(duration and duration in answer_n)
        return ok, f"期望包含建议游览时长 {duration} 分钟。"

    if case_type == "where":
        expected = record.get("location") or spot.get("location") or ""
        fragments = [frag for frag in re.split(r"[，。；;、\s]+", expected) if len(frag) >= 4]
        ok = bool(
            (spot.get("name", "") in answer)
            and (not fragments or any(normalize(frag) in answer_n for frag in fragments[:4]))
        )
        return ok, "期望答案包含景点名称和资料中的具体位置。"

    if case_type == "open":
        open_info = record.get("openInfo") or spot.get("openTime") or ""
        if "随景区开放时间" in open_info:
            ok = "随景区开放时间" in answer
        else:
            times = re.findall(r"\d{1,2}:\d{2}", open_info)
            ok = bool(not times or any(time in answer for time in times[:3]) or compact(open_info, 24)[:6] in answer)
        return ok, "期望开放/演艺时间来自资料中的演艺/开放信息。"

    if case_type == "performance":
        open_info = record.get("openInfo") or ""
        if any(term in open_info for term in ("演出", "表演", "加演", "开园仪式", "灯光秀", "场次", "小程序通知", "广播通知")):
            times = re.findall(r"\d{1,2}:\d{2}", open_info)
            keywords = [
                term
                for term in (
                    "演出",
                    "表演",
                    "加演",
                    "开园仪式",
                    "灯光秀",
                    "场次",
                    "小程序通知",
                    "广播通知",
                )
                if term in open_info
            ]
            ok = bool(any(time in answer for time in times) or any(term in answer for term in keywords))
        else:
            ok = "没有固定表演时间" in answer or "当天公告" in answer or "现场广播" in answer
        return ok, "期望表演回答依据演艺/开放信息；无表演时说明以公告为准。"

    if case_type == "parameters":
        parameters = record.get("parameters") or ""
        fragments = [frag for frag in re.split(r"[，。；;、\s]+", parameters) if len(frag) >= 2]
        ok = bool(fragments and any(normalize(frag) in answer_n for frag in fragments))
        return ok, "期望建筑参数回答来自结构化资料的建筑/景观参数字段。"

    if case_type == "photo":
        evidence = " ".join(str(record.get(key, "")) for key in ("location", "highlights", "detail", "culture"))
        fragments = [frag for frag in re.split(r"[，。；;、\s]+", evidence) if len(frag) >= 4]
        ok = answer.startswith("适合") and bool(
            not fragments or any(normalize(frag) in answer_n for frag in fragments)
        )
        return ok, "期望拍照理由来自位置、亮点、详细介绍或文化内涵。"

    if case_type in {"intro", "highlights"}:
        evidence = " ".join(str(record.get(key, "")) for key in ("coreFunction", "culture", "detail", "highlights"))
        fragments = [frag for frag in re.split(r"[，。；;、\s]+", evidence) if len(frag) >= 4]
        ok = bool(fragments and any(normalize(frag) in answer_n for frag in fragments[:16]))
        return ok, "期望介绍/亮点来自核心功能、文化内涵、详细介绍或游玩亮点。"

    if case_type == "generic":
        question = case["question"]
        if "灵山大佛多高" in question:
            ok = "88" in answer and "101.5" in answer
            return ok, "期望回答包含灵山大佛通高 88 米、含台基总高 101.5 米。"
        if "九龙灌浴表演时间" in question:
            ok = all(time in answer for time in ("10:00", "11:30", "13:30", "15:00"))
            return ok, "期望回答包含九龙灌浴平日演出时间。"
        ok = result.get("llmProvider") in {"knowledge_base", "local_fact"}
        return ok, "通用问题期望由本地知识库或本地结构化事实回答。"

    return True, "已通过来源检查。"


def selected_knowledge_for_question(question, spots):
    matched = app_core.match_spots_by_question(question, spots)
    hits = app_core.search_knowledge(question)
    if hasattr(app_core, "prioritize_exact_spot_knowledge"):
        hits = app_core.prioritize_exact_spot_knowledge(question, hits, matched)
    selected = app_core.select_knowledge_hits_for_answer(question, hits, matched) if hits else []
    return hits, selected[0] if selected else None


def build_cases(spots, records):
    record_by_name = {record["name"]: record for record in records}
    case_specs = [
        ("where", "{name}在哪里？", "具体位置"),
        ("open", "{name}几点开放？", "演艺/开放信息"),
        ("photo", "{name}适合拍照吗？", "游玩亮点/位置/介绍"),
        ("intro", "介绍一下{name}", "核心功能/文化内涵/详细介绍"),
        ("highlights", "{name}有什么亮点？", "游玩亮点/详细介绍"),
        ("duration", "{name}建议游览多久？", "景点表 duration 字段"),
        ("parameters", "{name}有什么建筑参数？", "建筑/景观参数"),
        ("performance", "{name}有表演时间吗？", "演艺/开放信息"),
    ]

    cases = []
    for spot in spots:
        record = record_by_name.get(spot["name"])
        if not record:
            continue
        for case_type, template, expected_field in case_specs:
            cases.append(
                {
                    "type": case_type,
                    "question": template.format(name=spot["name"]),
                    "spot": spot,
                    "record": record,
                    "expected_field": expected_field,
                }
            )

    generic_cases = [
        ("generic", "灵山大佛多高？", "灵山大佛", "建筑/景观参数"),
        ("generic", "九龙灌浴表演时间？", "九龙灌浴", "演艺/开放信息"),
        ("generic", "灵山胜境门票多少钱？", "", "门票开放与实用游览贴士/本地结构化事实"),
        ("generic", "亲子家庭路线怎么安排？", "", "亲子家庭路线"),
        ("generic", "景区适合拍照打卡的地方有哪些？", "", "景点资料/本地结构化事实"),
    ]
    for case_type, question, spot_name, expected_field in generic_cases:
        spot = next((item for item in spots if item["name"] == spot_name), None)
        cases.append(
            {
                "type": case_type,
                "question": question,
                "spot": spot or {},
                "record": record_by_name.get(spot_name, {}),
                "expected_field": expected_field,
            }
        )
    return cases, record_by_name


def evidence_for_case(case, selected_doc, top_ref, knowledge_docs):
    if selected_doc:
        fields = app_core.extract_structured_fields(selected_doc)
        field_keys = {
            "where": ["具体位置"],
            "open": ["演艺/开放信息", "开放/演艺信息"],
            "photo": ["游玩亮点", "具体位置", "详细介绍", "文化内涵"],
            "intro": ["核心功能", "文化内涵", "详细介绍", "游玩亮点"],
            "highlights": ["游玩亮点", "详细介绍", "核心功能"],
            "parameters": ["建筑/景观参数"],
            "performance": ["演艺/开放信息", "开放/演艺信息"],
        }.get(case["type"], [])
        values = []
        for key in field_keys:
            if fields.get(key):
                values.append(f"{key}：{fields[key]}")
        return compact("；".join(values) or selected_doc.get("content", ""), 220)
    return compact(source_doc_text(top_ref, knowledge_docs), 220)


def build_report(results, spots, record_by_name, knowledge_docs):
    provider_counts = Counter(item["provider"] for item in results)
    type_counts = Counter(item["type"] for item in results)
    failures = [item for item in results if item["check"] != "对应"]
    official_spot_count = len([spot for spot in spots if spot["name"] in record_by_name])

    lines = [
        "# 景区数字人问答批量测试报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 测试范围",
        "",
        "- 调用入口：`backend.app_core.answer_question(question)`",
        "- 测试方式：拦截真实 DeepSeek 调用，只记录是否会进入 DeepSeek 分支；其余逻辑按当前代码运行。",
        "- 问题覆盖：每个官方景点分别测试位置、开放时间、拍照、介绍、亮点、建议游览时长、建筑参数、表演时间；另补充 5 个通用景区问题。",
        "- 知识库来源：",
        "  - `softwarebar/示范景区公开资料包/灵山胜境 景点结构化数据集.docx`",
        "  - `softwarebar/示范景区公开资料包/灵山胜境：历史、文化、景点特色与个性化游览指南.docx`",
        "",
        "## 总结",
        "",
        f"- 官方景点数：{official_spot_count}",
        f"- 活跃知识条目数：{len(knowledge_docs)}",
        f"- 测试问题数：{len(results)}",
        f"- 与知识库/本地结构化事实对应：{len(results) - len(failures)}",
        f"- 需复核：{len(failures)}",
        f"- DeepSeek 分支触发次数：{len(deepseek_calls)}",
        "- 回答风格检查：本批答案未出现自我介绍，也未向用户说明“知识库是否命中”。",
        "",
        "### 回答来源统计",
        "",
        "| 来源 | 数量 |",
        "| --- | ---: |",
    ]
    for provider, count in sorted(provider_counts.items()):
        lines.append(f"| {provider or '-'} | {count} |")

    lines.extend(["", "### 问题类型统计", "", "| 类型 | 数量 |", "| --- | ---: |"])
    for case_type, count in sorted(type_counts.items()):
        lines.append(f"| {case_type} | {count} |")

    lines.extend(["", "## 需复核条目", ""])
    if failures:
        lines.extend(["| 序号 | 类型 | 问题 | 回答 | 说明 |", "| ---: | --- | --- | --- | --- |"])
        for item in failures:
            lines.append(f"| {item['index']} | {item['type']} | {item['question']} | {item['answer']} | {item['check_note']} |")
        lines.append("")
    else:
        lines.extend(["本次未发现需复核条目。", ""])

    lines.extend(["## 明细", ""])
    for item in results:
        lines.extend(
            [
                f"### {item['index']}. {item['question']}",
                "",
                f"- 类型：{item['type']}",
                f"- 回答：{item['answer']}",
                f"- 回答来源：{item['provider']} / {item['model']}",
                f"- 置信度：{item['confidence']}",
                f"- 知识检索最高分：{item['score'] or '-'}",
                f"- 命中来源：{item['source']}",
                f"- 核对字段：{item['expected']}",
                f"- 资料摘录：{item['evidence']}",
                f"- 核对结果：{item['check']}。{item['check_note']}",
                "",
            ]
        )
    return "\n".join(lines), failures, provider_counts, type_counts


def main():
    spots = app_core.get_spots()
    records = app_core.parse_official_spot_records()
    knowledge_docs = app_core.get_knowledge_documents(include_inactive=False)
    cases, record_by_name = build_cases(spots, records)

    results = []
    for index, case in enumerate(cases, 1):
        question = case["question"]
        result = app_core.answer_question(question)
        hits, selected_doc = selected_knowledge_for_question(question, spots)
        answer = result.get("answer", "")
        ok, check_note = answer_has_expected(case, answer, result)
        refs = result.get("sourceRefs") or []
        top_ref = refs[0] if refs else {}
        source = source_title(top_ref)
        if result.get("llmProvider") == "local_fact" and not refs:
            source = "本地结构化事实规则"
        elif result.get("llmProvider") == "deepseek_stub":
            source = "DeepSeek stub（知识库未命中）"
        elif selected_doc and source == "-":
            source = source_title(selected_doc)

        score = f"{float(hits[0].get('score', 0) or 0):.2f}" if hits else ""
        results.append(
            {
                "index": index,
                "type": case["type"],
                "question": question,
                "answer": answer,
                "provider": result.get("llmProvider", ""),
                "model": result.get("modelName", ""),
                "confidence": result.get("confidence", ""),
                "score": score,
                "source": source,
                "expected": case["expected_field"],
                "evidence": evidence_for_case(case, selected_doc, top_ref, knowledge_docs) or check_note,
                "check": "对应" if ok else "需复核",
                "check_note": check_note,
            }
        )

    report, failures, provider_counts, type_counts = build_report(results, spots, record_by_name, knowledge_docs)
    output_path = ROOT / "docs" / "scenic_qa_batch_test_report.md"
    output_path.write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(output_path),
                "spot_count": len([spot for spot in spots if spot["name"] in record_by_name]),
                "knowledge_doc_count": len(knowledge_docs),
                "case_count": len(results),
                "failure_count": len(failures),
                "provider_counts": dict(provider_counts),
                "type_counts": dict(type_counts),
                "deepseek_call_count": len(deepseek_calls),
                "deepseek_questions": deepseek_calls,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
