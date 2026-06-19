import math
import re
from collections import Counter


SYNONYM_GROUPS = [
    ("门票", "票价", "价格", "收费", "优惠", "免费", "免票"),
    ("表演", "演出", "节目", "时间", "场次"),
    ("路线", "游线", "怎么逛", "推荐", "行程", "安排"),
    ("停车", "交通", "入口", "怎么去", "到达", "车场"),
    ("拍照", "打卡", "观景", "出片"),
]


def normalize_text(value):
    return str(value or "").strip().lower()


def extract_terms(text):
    normalized = normalize_text(text)
    words = [word for word in re.split(r"[\s,，。！？!?.、；;：:（）()【】\[\]\"']+", normalized) if len(word) >= 2]
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized))
    grams = []
    for size in (2, 3, 4):
        grams.extend(cjk[index : index + size] for index in range(max(len(cjk) - size + 1, 0)))
    return list(dict.fromkeys(words + grams))


def split_sentences(text):
    parts = re.split(r"(?<=[。！？!?])", str(text or ""))
    return [part.strip() for part in parts if part.strip()]


def vectorize_text(text):
    terms = extract_terms(text)
    return Counter(terms)


def expand_query_terms(question, terms):
    normalized = normalize_text(question)
    expanded = list(terms)
    for group in SYNONYM_GROUPS:
        if any(word in normalized or word in terms for word in group):
            expanded.extend(group)
    return list(dict.fromkeys(expanded))


def cosine_similarity(left, right):
    if not left or not right:
        return 0.0
    common = set(left) & set(right)
    dot = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def search_documents(question, documents, limit=4):
    terms = expand_query_terms(question, extract_terms(question))
    question_vector = vectorize_text(" ".join([question, *terms]))
    normalized_question = normalize_text(question)
    scored = []

    for document in documents:
        title = normalize_text(document.get("title"))
        category = normalize_text(document.get("category"))
        content = normalize_text(document.get("content"))
        score = (
            cosine_similarity(question_vector, vectorize_text(title)) * 22
            + cosine_similarity(question_vector, vectorize_text(category)) * 12
            + cosine_similarity(question_vector, vectorize_text(content)) * 34
        )

        if len(normalized_question) >= 4 and normalized_question in content:
            score += 20
        for term in terms:
            if term in title:
                score += 8
            if term in category:
                score += 5
            if term in content:
                score += min(content.count(term), 3) * 2

        if score > 0:
            scored.append((round(score, 4), document))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"score": score, **document} for score, document in scored[:limit]]


def build_summary(question, documents, max_sentences=3, max_chars=260):
    terms = [term for term in extract_terms(question) if len(term) >= 2]
    selected = []
    for document in documents:
        sentences = split_sentences(document.get("content", ""))
        matched = [sentence for sentence in sentences if any(term in sentence for term in terms)]
        selected.extend(matched[:2] or sentences[:1])
        if len(selected) >= max_sentences:
            break
    summary = "".join(selected[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip("，,；;。") + "。"
    return summary
