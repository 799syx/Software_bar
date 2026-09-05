from __future__ import annotations

import importlib
import json
import os
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
os.environ["SCENIC_CHAT_FAST_MODE"] = "false"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

app_core = importlib.import_module("backend.app_core")


HIT_SPECS = [
    ("位置", "{name}在哪里？"),
    ("开放", "{name}几点开放？"),
    ("拍照", "{name}适合拍照吗？"),
    ("介绍", "介绍一下{name}"),
    ("亮点", "{name}有什么亮点？"),
    ("时长", "{name}建议游览多久？"),
    ("参数", "{name}有什么建筑参数？"),
    ("表演", "{name}有表演时间吗？"),
]


MISS_QUESTIONS = [
    "你好",
    "您好",
    "谢谢你",
    "你是谁？",
    "现在几点？",
    "今天星期几？",
    "讲个笑话",
    "帮我写一首诗",
    "给我一句鼓励的话",
    "用一句话解释人工智能",
    "量子计算是什么？",
    "Python 怎么读取 JSON 文件？",
    "JavaScript 里 promise 是什么？",
    "Excel 怎么冻结首行？",
    "电脑蓝屏怎么办？",
    "手机没电了怎么办？",
    "蓝牙耳机连不上怎么办？",
    "路由器怎么重启？",
    "番茄炒蛋怎么做？",
    "米饭煮硬了怎么办？",
    "咖啡太苦怎么调？",
    "怎么整理旅行箱？",
    "上海到北京高铁多久？",
    "杭州有什么好吃的？",
    "苏州园林有什么特点？",
    "南京博物院需要预约吗？",
    "北京今天限号吗？",
    "今天适合带伞吗？",
    "美元兑人民币现在多少？",
    "帮我翻译 hello world",
    "把早上好翻译成英文",
    "写一句英文欢迎语",
    "给我起一个活动标题",
    "帮我想一个团队口号",
    "写一条朋友圈文案",
    "写一段生日祝福",
    "写一封感谢信开头",
    "怎么提高睡眠质量？",
    "跑步前要热身吗？",
    "早上喝水好吗？",
    "怎么缓解紧张？",
    "如何制定学习计划？",
    "怎么背英语单词？",
    "如何做会议纪要？",
    "项目延期怎么沟通？",
    "简历怎么写更清楚？",
    "面试自我介绍怎么说？",
    "什么是现金流？",
    "复利是什么意思？",
    "股票和基金有什么区别？",
    "什么是通货膨胀？",
    "地球为什么有四季？",
    "月亮为什么会有阴晴圆缺？",
    "彩虹是怎么形成的？",
    "海水为什么是咸的？",
    "猫为什么喜欢晒太阳？",
    "狗为什么摇尾巴？",
    "植物为什么需要阳光？",
    "怎么给照片压缩大小？",
    "PDF 怎么转图片？",
    "Word 怎么生成目录？",
    "PPT 怎么统一字体？",
    "视频太大怎么压缩？",
    "键盘快捷键复制是什么？",
    "Windows 怎么截图？",
    "Mac 怎么截图？",
    "怎么设置闹钟？",
    "如何管理待办事项？",
    "怎么减少拖延？",
    "番茄工作法是什么？",
    "如何保持专注？",
    "怎么做预算表？",
    "买衣服怎么选尺码？",
    "洗衣服串色怎么办？",
    "白鞋怎么清洗？",
    "房间怎么收纳？",
    "盆栽多久浇一次水？",
    "怎么判断水果熟没熟？",
    "运动鞋磨脚怎么办？",
    "出门忘带身份证怎么办？",
    "火车票怎么改签？",
    "飞机延误怎么办？",
    "酒店入住需要什么证件？",
    "怎么查快递？",
    "如何保护个人隐私？",
    "密码怎么设置更安全？",
    "手机丢了怎么办？",
    "银行卡丢了怎么办？",
    "怎么识别诈骗电话？",
    "什么是云计算？",
    "什么是数据库索引？",
    "HTTP 和 HTTPS 有什么区别？",
    "前端和后端有什么区别？",
    "什么是 API？",
    "怎么写单元测试？",
    "Git 怎么撤销上一次提交？",
    "Docker 是做什么的？",
    "Linux 怎么查看当前目录？",
    "SQL 怎么查询前十条？",
    "帮我写一句晚安",
    "请用三个词形容夏天",
]


def compact(value, limit=140):
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ，。；;、") + "..."


def build_hit_questions():
    spots = app_core.get_spots()
    questions = []
    for spot in spots:
        for case_type, template in HIT_SPECS:
            questions.append({"group": "hit", "type": case_type, "question": template.format(name=spot["name"])})
    return questions[:100]


def build_miss_questions():
    return [{"group": "miss", "type": "非知识库", "question": question} for question in MISS_QUESTIONS[:100]]


def run_case(index, case):
    started = time.perf_counter()
    result = app_core.answer_question(case["question"])
    latency_ms = int((time.perf_counter() - started) * 1000)
    provider = result.get("llmProvider", "")
    expected_provider = "knowledge_base" if case["group"] == "hit" else "deepseek"
    passed = provider == expected_provider
    source_refs = result.get("sourceRefs") or []
    first_ref = source_refs[0] if source_refs else {}
    return {
        "index": index,
        "group": case["group"],
        "type": case["type"],
        "question": case["question"],
        "answer": result.get("answer", ""),
        "provider": provider,
        "model": result.get("modelName", ""),
        "confidence": result.get("confidence", ""),
        "fallback": result.get("fallback", False),
        "latencyMs": latency_ms,
        "source": first_ref.get("title", "-"),
        "sourceCategory": first_ref.get("category", ""),
        "passed": passed,
    }


def build_report(rows):
    provider_counts = Counter(row["provider"] for row in rows)
    group_counts = Counter(row["group"] for row in rows)
    failures = [row for row in rows if not row["passed"]]
    lines = [
        "# 200 条问答命中/不命中测试报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 结论",
        "",
        f"- 总问题数：{len(rows)}",
        f"- 命中知识库组：{group_counts.get('hit', 0)}",
        f"- 不命中知识库组：{group_counts.get('miss', 0)}",
        f"- 分支符合预期：{len(rows) - len(failures)}",
        f"- 分支异常：{len(failures)}",
        "",
        "### 来源统计",
        "",
        "| 来源 | 数量 |",
        "| --- | ---: |",
    ]
    for provider, count in sorted(provider_counts.items()):
        lines.append(f"| {provider or '-'} | {count} |")
    lines.extend(["", "## 异常条目", ""])
    if failures:
        lines.extend(["| 序号 | 分组 | 问题 | 实际来源 | 回答 |", "| ---: | --- | --- | --- | --- |"])
        for row in failures:
            lines.append(f"| {row['index']} | {row['group']} | {row['question']} | {row['provider']} | {compact(row['answer'], 90)} |")
    else:
        lines.append("本次未发现分支异常。")

    lines.extend(["", "## 明细", ""])
    lines.extend(["| 序号 | 分组 | 类型 | 问题 | 实际来源 | 回答 | 来源/模型 | 耗时ms | 结果 |", "| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |"])
    for row in rows:
        status = "通过" if row["passed"] else "异常"
        source = row["source"] if row["group"] == "hit" else row["model"]
        lines.append(
            f"| {row['index']} | {row['group']} | {row['type']} | {row['question']} | {row['provider']} | "
            f"{compact(row['answer'], 120)} | {source} | {row['latencyMs']} | {status} |"
        )
    return "\n".join(lines)


def main():
    cases = [*build_hit_questions(), *build_miss_questions()]
    rows = []
    for index, case in enumerate(cases, 1):
        rows.append(run_case(index, case))
        if index % 20 == 0:
            print(json.dumps({"progress": index, "total": len(cases)}, ensure_ascii=False))
    report = build_report(rows)
    output_path = ROOT / "docs" / "qa_200_hit_miss_report.md"
    output_path.write_text(report, encoding="utf-8")
    failures = [row for row in rows if not row["passed"]]
    print(
        json.dumps(
            {
                "output": str(output_path),
                "total": len(rows),
                "hit_count": sum(1 for row in rows if row["group"] == "hit"),
                "miss_count": sum(1 for row in rows if row["group"] == "miss"),
                "failure_count": len(failures),
                "provider_counts": dict(Counter(row["provider"] for row in rows)),
                "failed_questions": [row["question"] for row in failures[:20]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
