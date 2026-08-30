"""Pure topic matching for the Research Universe knowledge graph."""

from __future__ import annotations

import re
import unicodedata

import jieba


TOPIC_ALIASES = {
    "Antarctic Ice Sheet": ["南极冰盖", "南极洲冰盖"],
    "CDW Intrusion": ["环南极深层水", "绕极深层水", "温水入侵", "暖水入侵", "cdw"],
    "Cross-shelf Heat Transport": ["跨陆架热输送", "跨冰架热输送", "热量输送"],
    "Ice-shelf Basal Melt": ["冰架基底融化", "基底融化", "冰架融化", "冰架底融"],
    "Freshwater Feedback": ["淡水反馈", "融水反馈", "淡化反馈"],
    "Buttressing": ["冰架支撑", "支撑效应", "背应力"],
    "Grounding Line Retreat": ["接地线后退", "接地线退缩", "接地线迁移", "接地线"],
    "MISI": ["海洋冰盖不稳定", "海洋冰盖不稳定性", "逆坡床", "misi"],
    "MICI": ["海洋冰崖不稳定", "水力压裂", "冰崖失稳", "mici"],
    "Basal Sliding": ["基底滑动", "冰底滑动", "底部摩擦"],
    "GIA": ["冰川均衡调整", "冰后回弹", "基岩回弹", "gia"],
    "Bed Topography": ["床面地形", "冰下地形", "基岩地形"],
    "Geothermal Heat Flux": ["地热通量", "地热热流"],
    "Subglacial Hydrology": ["冰下水文", "冰下湖", "冰下排水"],
    "Satellite Altimetry": ["卫星测高", "高度计", "表面高程"],
    "InSAR Velocity": ["insar", "雷达干涉", "冰流速度"],
    "GRACE / GRACE-FO": ["grace", "grace-fo", "卫星重力", "重力测量", "质量平衡"],
    "Radar & Field Data": ["雷达与野外数据", "探冰雷达", "野外观测"],
    "Pliocene": ["上新世", "中上新世"],
    "Last Interglacial": ["末次间冰期", "伊敏间冰期"],
    "Ice Cores": ["冰芯", "冰核"],
    "Marine Sediments": ["海洋沉积物", "海底沉积物", "沉积岩芯"],
    "Sea-level Contribution": ["海平面贡献", "海平面上升", "全球平均海平面"],
    "Coupled Models": ["耦合模型", "冰海耦合", "地球系统模型"],
    "Uncertainty Quantification": ["不确定性量化", "概率预测", "集合模拟"],
    "AI for Earth Observation": ["地球观测人工智能", "机器学习", "深度学习"],
}

_EN_STOPWORDS = {
    "about", "and", "are", "does", "for", "from", "how", "important",
    "in", "is", "of", "paper", "the", "this", "to", "what", "why",
}
_ZH_STOPWORDS = {
    "为什么", "什么", "如何", "怎么", "怎样", "重要", "影响", "有关",
    "关于", "论文", "综述", "南极", "冰盖", "请问", "可以",
}


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).casefold().strip()


def _tokens(text: str) -> set[str]:
    normalized = _normalize(text)
    result = {
        token for token in re.findall(r"[a-z0-9][a-z0-9+&./-]*", normalized)
        if len(token) > 1 and token not in _EN_STOPWORDS
    }
    if re.search(r"[\u3400-\u9fff]", normalized):
        result.update(
            token.strip() for token in jieba.lcut(normalized)
            if len(token.strip()) > 1 and token.strip() not in _ZH_STOPWORDS
        )
    return result


def match_topic(
    query: str,
    topic_names: list[str],
    *,
    topic_keywords: dict[str, list[str]] | None = None,
    topic_context: dict[str, str] | None = None,
    aliases: dict[str, list[str]] | None = None,
) -> tuple[str, int]:
    """Return the best local graph topic and a deterministic relevance score."""

    names = list(topic_names or [])
    default = "Antarctic Ice Sheet" if "Antarctic Ice Sheet" in names else (names[0] if names else "")
    normalized_query = _normalize(query)
    if not normalized_query or not names:
        return default, 0

    query_tokens = _tokens(normalized_query)
    keyword_map = topic_keywords or {}
    context_map = topic_context or {}
    alias_map = TOPIC_ALIASES if aliases is None else aliases
    best_name, best_score = default, 0

    for name in names:
        phrases = [name, *keyword_map.get(name, []), *alias_map.get(name, [])]
        score = 0
        candidate_tokens: set[str] = set()
        for phrase in phrases:
            normalized_phrase = _normalize(phrase)
            if not normalized_phrase:
                continue
            phrase_tokens = _tokens(normalized_phrase)
            candidate_tokens.update(phrase_tokens)
            if normalized_phrase in normalized_query:
                score += 24 + min(16, len(normalized_phrase))
        score += 5 * len(query_tokens & candidate_tokens)
        score += 2 * len(query_tokens & _tokens(context_map.get(name, "")))
        if name != default and score > 0:
            score += 2
        if score > best_score:
            best_name, best_score = name, score

    return best_name, best_score
