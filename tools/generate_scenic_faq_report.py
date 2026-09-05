from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import generate_diverse_qa_200_report as base


ROOT = Path(__file__).resolve().parents[1]


def build_cases():
    local = ["knowledge_base", "local_fact", "local"]
    return [
        base.case("开放入园", "景区几点开门？", [], [["开放", "公告", "9 点", "9点"]], local),
        base.case("开放入园", "灵山梵宫几点开放？", ["灵山梵宫"], [["9:00", "17:00"]], local),
        base.case("开放入园", "五印坛城几点闭馆？", ["五印坛城"], [["17:00", "16:30", "闭馆"]], local),
        base.case("开放入园", "晚上还能进灵山胜境吗？", [], [["公告", "开放", "闭园", "现场"]], local),
        base.case("开放入园", "节假日开放时间会变吗？", [], [["公告", "广播", "客流", "现场"]], local),
        base.case("开放入园", "需要提前预约入园吗？", [], [["公告", "小程序", "预约", "现场"]], local),
        base.case("票务价格", "成人票多少钱？", ["210"], [["成人票", "门票"]], local),
        base.case("票务价格", "学生票怎么买？", [], [["半价", "学生", "证件", "105"]], local),
        base.case("票务价格", "老人票有优惠吗？", [], [["60-69", "70", "半价", "免票"]], local),
        base.case("票务价格", "儿童怎么买票？", [], [["6 周岁", "1.4 米", "半价", "免票"]], local),
        base.case("票务价格", "军人免票吗？", [], [["现役军人", "免票", "证件"]], local),
        base.case("票务价格", "残疾人有优惠吗？", [], [["残疾人", "免票", "证件"]], local),
        base.case("票务价格", "观光车票多少钱？", ["40"], [["观光车"]], local),
        base.case("票务价格", "门票加观光车联票多少钱？", ["225"], [["联票", "观光车"]], local),
        base.case("票务价格", "现场买票可以吗？", [], [["现场", "公告", "服务中心", "证件"]], local),
        base.case("票务价格", "买票需要身份证吗？", [], [["证件", "核验", "身份证", "公告"]], local),
        base.case("票务价格", "票买错了能退吗？", [], [["购票平台", "退票", "公告", "服务中心"]], local),
        base.case("交通停车", "停车场在哪里？", [], [["停车", "现场指引", "服务中心"]], local),
        base.case("交通停车", "自驾车停哪里？", [], [["停车", "现场指引", "服务中心"]], local),
        base.case("交通停车", "停车收费吗？", [], [["停车", "现场", "公告", "服务中心"]], local),
        base.case("交通停车", "从入口到游客服务中心怎么走？", ["游客服务中心"], [["入口", "服务区"]], local),
        base.case("交通停车", "观光车在哪里坐？", [], [["观光车", "换乘", "服务中心", "现场"]], local),
        base.case("交通停车", "想少走路可以坐观光车吗？", [], [["观光车", "体力", "老人儿童", "换乘"]], local),
        base.case("服务设施", "厕所在哪里？", [], [["卫生间", "厕所", "服务中心", "导视"]], local),
        base.case("服务设施", "母婴室在哪里？", [], [["母婴", "服务中心", "工作人员"]], local),
        base.case("服务设施", "能寄存行李吗？", [], [["寄存", "服务中心", "现场"]], local),
        base.case("服务设施", "手机没电了怎么办？", [], [["充电", "服务中心", "工作人员"]], local),
        base.case("服务设施", "游客服务中心能办什么？", ["游客服务中心"], [["寄存", "母婴", "失物招领", "医药箱", "无障碍"]], local),
        base.case("服务设施", "有轮椅可以租吗？", [], [["轮椅", "无障碍", "服务中心"]], local),
        base.case("服务设施", "行动不便怎么游览？", [], [["轮椅", "无障碍", "观光车", "服务中心"]], local),
        base.case("安全求助", "我迷路了怎么办？", [], [["游客服务中心", "工作人员", "现场"]], local),
        base.case("安全求助", "孩子走丢了怎么办？", [], [["游客服务中心", "工作人员", "广播", "安保"]], local),
        base.case("安全求助", "东西丢了怎么办？", [], [["失物招领", "服务中心", "工作人员"]], local),
        base.case("安全求助", "身体不舒服怎么办？", [], [["服务中心", "工作人员", "急救", "医药箱"]], local),
        base.case("安全求助", "摔倒受伤怎么办？", [], [["工作人员", "服务中心", "急救", "安保"]], local),
        base.case("天气应对", "下雨天还能游览吗？", [], [["防滑", "雨天", "天气", "公告"]], local),
        base.case("天气应对", "下雨天登云道要注意什么？", [], [["防滑", "台阶", "雨天", "体力"]], local),
        base.case("天气应对", "夏天游览要注意什么？", [], [["防晒", "水", "体力", "天气"]], local),
        base.case("天气应对", "冬天去要穿什么？", [], [["保暖", "运动鞋", "雨伞", "充电宝"]], local),
        base.case("路线安排", "第一次来灵山胜境怎么玩？", [], [["九龙灌浴", "灵山大佛", "灵山梵宫", "五印坛城"]], local),
        base.case("路线安排", "亲子家庭路线怎么安排？", ["九龙灌浴", "五印坛城"], [["百子戏弥勒", "灵山梵宫"]], local),
        base.case("路线安排", "带老人怎么走轻松？", [], [["观光车", "游客服务中心", "无障碍", "少走"]], local),
        base.case("路线安排", "两个小时怎么逛？", [], [["灵山大照壁", "九龙灌浴", "灵山梵宫", "灵山大佛"]], local),
        base.case("路线安排", "半天时间怎么安排？", [], [["路线", "九龙灌浴", "灵山大佛", "灵山梵宫"]], local),
        base.case("路线安排", "一天时间怎么安排？", [], [["路线", "九龙灌浴", "灵山大佛", "灵山梵宫", "五印坛城"]], local),
        base.case("路线安排", "想看佛教文化怎么安排？", [], [["灵山大佛", "灵山梵宫", "五印坛城"]], local),
        base.case("路线安排", "喜欢历史文化怎么逛？", ["灵山大照壁", "五印坛城"], [["祥符禅寺", "灵山大佛"]], local),
        base.case("路线安排", "自然风光路线推荐一下", ["佛足坛", "九龙灌浴"], [["菩提大道", "曼飞龙塔"]], local),
        base.case("路线安排", "哪里适合拍照打卡？", ["五印坛城"], [["灵山大照壁", "九龙灌浴", "曼飞龙塔"]], local),
        base.case("景点问路", "五印坛城怎么走？", ["五印坛城"], [["景观栈道", "灵山梵宫"]], local),
        base.case("景点问路", "从灵山梵宫到五印坛城怎么走？", ["五印坛城"], [["景观栈道", "灵山梵宫"]], local),
        base.case("景点问路", "入口到灵山大佛怎么走？", ["灵山大佛"], [["游客服务中心", "灵山大照壁", "五明桥"]], local),
        base.case("景点问路", "九龙灌浴在哪里？", ["九龙灌浴"], [["菩提大道北端", "中轴线"]], local),
        base.case("景点问路", "曼飞龙塔在哪里？", ["曼飞龙塔"], [["五印坛城北侧", "香水海北岸"]], local),
        base.case("景点问路", "香月花街怎么走？", ["香月花街"], [["拈花广场", "五灯湖"]], local),
        base.case("演出活动", "九龙灌浴几点表演？", ["10:00", "11:30", "13:30", "15:00"], [], local),
        base.case("演出活动", "九龙灌浴表演多久？", [], [["15分钟", "15 分钟"]], local),
        base.case("演出活动", "梵宫吉祥颂几点演？", ["10:35", "11:30", "14:00", "16:00"], [["20分钟", "20 分钟"]], local),
        base.case("演出活动", "五印坛城有表演吗？", ["五印坛城"], [["没有固定", "公告", "广播"]], local),
        base.case("演出活动", "香月花街有表演吗？", ["香月花街"], [["巡游", "广播", "不定时"]], local),
        base.case("拍照打卡", "灵山大佛哪里拍照好看？", ["灵山大佛"], [["地标", "佛脚", "太湖", "夕阳", "拍"]], local),
        base.case("拍照打卡", "五印坛城适合拍什么？", ["五印坛城"], [["建筑", "环境", "拍照", "打卡"]], local),
        base.case("拍照打卡", "灵山梵宫适合拍照吗？", ["灵山梵宫"], [["适合", "建筑", "香水海"]], local),
        base.case("拍照打卡", "九龙灌浴适合拍照吗？", ["九龙灌浴"], [["适合", "动态", "莲花", "喷泉"]], local),
        base.case("餐饮购物", "景区里有什么素食推荐？", [], [["梵宫素斋", "素面", "灵山精舍"]], local),
        base.case("餐饮购物", "哪里能吃素面？", [], [["素面", "35", "灵山精舍"]], local),
        base.case("餐饮购物", "香月花街能购物吗？", ["香月花街"], [["文创", "商铺", "餐饮", "购物"]], local),
        base.case("文化礼仪", "佛教场所可以拍照吗？", [], [["不随意拍照", "现场提示", "尊重宗教"]], local),
        base.case("文化礼仪", "参观佛像能摸吗？", [], [["不触摸佛像", "保持安静", "尊重宗教"]], local),
        base.case("文化礼仪", "在寺庙里要注意什么？", [], [["保持安静", "尊重宗教", "不触摸"]], local),
        base.case("文化讲解", "灵山大佛有多高？", ["88"], [["101.5", "725吨"]], local),
        base.case("文化讲解", "灵山大佛手印是什么意思？", [], [["无畏印", "与愿印", "痛苦", "欢乐"]], local),
        base.case("文化讲解", "216级登云道有什么寓意？", ["216"], [["108烦恼", "108愿望"]], local),
        base.case("文化讲解", "五明桥代表什么？", [], [["声明", "因明", "内明", "医方明", "工巧明"]], local),
        base.case("文化讲解", "五印坛城有什么互动体验？", [], [["绕坛城", "转动转经筒", "藏香"]], local),
        base.case("文化讲解", "灵山梵宫为什么重要？", [], [["世界佛教论坛", "佛教艺术殿堂"]], local),
        base.case("文化讲解", "祥符禅寺有什么历史？", [], [["唐代", "北宋大中祥符", "千年古刹"]], local),
        base.case("定位扫码", "定位不准怎么办？", [], [["开阔", "手动", "照片", "重试", "服务中心"]], local),
        base.case("定位扫码", "扫码定位失败怎么办？", [], [["手动", "服务中心", "标识牌", "重试"]], local),
        base.case("定位扫码", "图片识别不出来怎么办？", [], [["重新拍摄", "文字问答", "定位", "服务中心"]], local),
        base.case("其他限制", "可以带宠物吗？", [], [["公告", "服务中心", "现场", "宠物"]], local),
        base.case("其他限制", "能飞无人机吗？", [], [["公告", "现场", "安全", "无人机"]], local),
        base.case("其他限制", "景区可以吸烟吗？", [], [["禁烟", "指定区域", "现场"]], local),
    ]


def build_report(rows):
    failures = [row for row in rows if not row["passed"]]
    category_counts = Counter(row["category"] for row in rows)
    category_failures = Counter(row["category"] for row in failures)
    lines = [
        "# 景区常见问题专项测试报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总结",
        "",
        f"- 总题数：{len(rows)}",
        f"- 通过：{len(rows) - len(failures)}",
        f"- 未通过：{len(failures)}",
        f"- 通过率：{(len(rows) - len(failures)) / max(1, len(rows)):.1%}",
        "",
        "| 类型 | 数量 | 未通过 |",
        "| --- | ---: | ---: |",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {count} | {category_failures.get(category, 0)} |")

    lines.extend(["", "## 未通过条目", ""])
    if failures:
        lines.extend(["| 序号 | 类型 | 问题 | 来源 | 回答 | 原因 |", "| ---: | --- | --- | --- | --- | --- |"])
        for row in failures:
            lines.append(
                f"| {row['index']} | {row['category']} | {row['question']} | {row['provider']} | "
                f"{base.compact(row['answer'], 100)} | {row['message']} |"
            )
    else:
        lines.append("本次专项常见问题全部通过。")

    lines.extend(["", "## 明细", ""])
    lines.extend(["| 序号 | 类型 | 问题 | 来源 | 回答 | 结果 |", "| ---: | --- | --- | --- | --- | --- |"])
    for row in rows:
        status = "通过" if row["passed"] else "未通过"
        lines.append(
            f"| {row['index']} | {row['category']} | {row['question']} | {row['provider']} | "
            f"{base.compact(row['answer'], 120)} | {status} |"
        )
    return "\n".join(lines)


def main():
    base.app_core.init_database()
    rows = base.run_cases(build_cases())
    output_path = ROOT / "docs" / "scenic_faq_report.md"
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
                "failedQuestions": [row["question"] for row in failures],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
