import json
import os
import re
from copy import deepcopy

from core.data import resource_path
from core.paths import settings_path


_DEFAULT_LOCALE = "en"
_LOCALE_DIR = resource_path("locales")
_CACHE = {}
_EXACT_CACHE = None
_LOCALIZED_MARKER = "_ATLAS_I18N_LOCALIZED"
_ORIGINALS_MARKER = "_ATLAS_I18N_ORIGINALS"
_CONFIG_PATH = settings_path()
_HOOKS_INSTALLED = False
_PROTECTED_TERMS = (
    "OpenAI",
    "DeepSeek",
    "Ollama",
    "ChatGPT",
    "RAG",
    "API",
    "CDW",
    "MISI",
    "MICI",
    "GIA",
    "GRACE",
    "GRACE-FO",
    "GNSS",
    "InSAR",
    "AUV",
    "CTD",
    "PDF",
    "Qt",
)
_TERM_FIXES = {
    "打开AI": "OpenAI",
    "打开 AI": "OpenAI",
    "Open AI": "OpenAI",
    "钥匙": "密钥",
    "模特": "模型",
    "模型 回复": "模型回复",
    "原纸": "原始论文",
    "纸质段落": "论文段落",
    "纸张段落": "论文段落",
    "冰原": "冰盖",
    "迷你研究实验室": "迷你科研实验室",
    "AI展示台": "AI 可视化器",
    "本地Ollama": "本地 Ollama",
    "Select 本地 Ollama, DeepSeek API, or OpenAI API.": "选择本地 Ollama、DeepSeek API 或 OpenAI API。",
}
_MANUAL_ZH = {
    "AI ANSWER": "AI 答案",
    "AI MODULE MATCHING": "AI 模块匹配",
    "EVIDENCE AND AI ANSWER": "证据与 AI 答案",
    "EVIDENCE BUILDER": "证据构建器",
    "OBSERVATION SUMMARY": "观测摘要",
    "OBSERVATION": "观测",
    "RESULT": "结果",
    "MEASUREMENT": "测量",
    "VISUAL LAYER": "可视图层",
    "Region": "区域",
    "Region:": "区域：",
    "Type": "类型",
    "Type:": "类型：",
    "Type: Fast outlet glacier": "类型：快速出口冰川",
    "Main theme": "核心主题",
    "Main theme:": "核心主题：",
    "PHYSICAL-PROCESS CONTEXT": "物理过程背景",
    "SELECTED FRONTIER": "已选前沿方向",
    "SLIDE-READY EXPORT TEXT": "可直接用于幻灯片的文本",
    "WHY IT MATTERS NOW": "为什么现在重要",
    "Evidence-only mode": "仅证据模式",
    "Each selected sensor contributes a different evidence dimension; together they assemble a scientific conclusion.": "每个被选中的传感器都会提供不同维度的证据；它们共同组合成一个科学结论。",
    "Evidence only": "仅证据",
    "Search evidence": "检索证据",
    "Ask AI and focus map": "询问 AI 并定位图谱",
    "Research Copilot": "科研助手",
    "AI Backend": "AI 后端",
    "API settings": "API 设置",
    "Save & Test Connection": "保存并测试连接",
    "Save & Test DeepSeek": "保存并测试 DeepSeek",
    "Save & Test OpenAI": "保存并测试 OpenAI",
    "Test Local Ollama": "测试本地 Ollama",
    "Model": "模型",
    "Key question": "关键问题",
    "KEY QUESTION": "关键问题",
    "WHY IT MATTERS": "重要性",
    "RESEARCH STATUS": "研究状态",
    "KEY REGIONS / LINKED TOPICS": "关键区域 / 关联主题",
    "Core system": "核心系统",
    "Research area": "研究领域",
    "Research hub": "研究枢纽",
    "Research frontier": "研究前沿",
    "Case Study": "案例研究",
    "Observation layers": "观测图层",
    "Multi-layer mode": "多图层模式",
    "Case": "案例",
    "Primary layer": "主图层",
    "Visible layers": "可见图层",
    "Measures": "测量内容",
    "Observed": "观测结果",
    "Synthesis": "综合判断",
    "For": "对于",
    "these layers support the theme": "这些图层共同支撑这一主题",
    "Case context": "案例背景",
    "Main message": "核心信息",
    "Scientific Story Engine": "科学故事引擎",
    "CURRENT LENS": "当前视角",
    "SLIDE-READY CHAIN": "幻灯片叙事链",
    "Reset": "重置",
    "Begin Story": "开始故事",
    "Pause": "暂停",
    "Resume": "继续",
    "Interactive Antarctic Ice Sheet Simulator": "交互式南极冰盖模拟器",
    "3D Conceptual Antarctic Ice Sheet Simulator": "3D 概念南极冰盖模拟器",
    "Conceptual Ice Shelf Buttressing Experiment": "概念冰架支撑实验",
    "ICE SHELF BREAKUP": "冰架破裂",
    "High impact + high uncertainty = frontier zone": "高影响 + 高不确定性 = 前沿区域",
    "Compass": "罗盘",
    "Timeline": "时间线",
    "Region map": "区域地图",
    "Proposal builder": "提案构建器",
    "Sea-level impact": "海平面影响",
    "Scientific uncertainty": "科学不确定性",
    "Directly observable": "可直接观测",
    "Observability": "可观测性",
    "High": "高",
    "Low": "低",
    "Conceptual Region Map": "概念区域图",
    "Generated Research Proposal Seed": "研究计划种子",
    "Knowledge gap": "知识缺口",
    "Key gap": "关键缺口",
    "Beginner-researcher angle": "初学研究者视角",
    "Starter questions": "入门问题",
    "Search matches": "搜索匹配",
    "Matching pages": "匹配页面",
    "Select page": "选择页面",
    "Page": "第",
    "Read Raw Paper": "阅读原始论文",
    "AI Visualizer": "AI 可视化器",
    "Mini Research Lab": "迷你科研实验室",
    "Research Universe": "研究宇宙",
    "Antarctic System": "南极系统",
    "Research Compass": "研究罗盘",
    "Antarctic Ice Sheet": "南极冰盖",
    "Antarctic Research Universe": "南极研究宇宙",
    "Ask a question; AI locates the matching node. You can also click any sphere manually.": "提出问题后，AI 会定位匹配节点；你也可以手动点击任意球体。",
    "Click a sphere · Ask below · matched module auto-focuses here": "点击球体 · 在下方提问 · 匹配模块会在此自动聚焦",
    "Click a sphere or ask below; the matching research node stays in focus.": "点击球体或在下方提问；匹配的研究节点会保持聚焦。",
    "Core": "核心",
    "Ocean": "海洋",
    "Ice Dynamics": "冰动力学",
    "Solid Earth": "固体地球",
    "Observations": "观测",
    "Paleoclimate": "古气候",
    "Future Projections": "未来预测",
    "CDW Intrusion": "CDW 入侵",
    "Cross-shelf Heat Transport": "跨陆架热输送",
    "Ice-shelf Basal Melt": "冰架基底融化",
    "Freshwater Feedback": "淡水反馈",
    "Buttressing": "支撑作用",
    "Grounding Line Retreat": "接地线后退",
    "Basal Sliding": "基底滑动",
    "Bed Topography": "冰下地形",
    "Geothermal Heat Flux": "地热通量",
    "Subglacial Hydrology": "冰下水文",
    "Satellite Altimetry": "卫星测高",
    "Altimetry": "测高",
    "InSAR Velocity": "InSAR 速度",
    "Radar & Field Data": "雷达与野外数据",
    "Pliocene": "上新世",
    "Last Interglacial": "末次间冰期",
    "Ice Cores": "冰芯",
    "Marine Sediments": "海洋沉积物",
    "Sea-level Contribution": "海平面贡献",
    "Coupled Models": "耦合模型",
    "Uncertainty Quantification": "不确定性量化",
    "AI for Earth Observation": "AI 地球观测",
    "Active frontier": "活跃前沿",
    "High uncertainty": "高度不确定",
    "Observed but hard to model": "已被观测但难以建模",
    "Emerging feedback": "新兴反馈",
    "Core mechanism": "核心机制",
    "Central research target": "核心研究目标",
    "High-impact uncertainty": "高影响不确定性",
    "Debated mechanism": "有争议的机制",
    "Difficult to observe": "难以观测",
    "Important feedback": "重要反馈",
    "Critical boundary data": "关键边界数据",
    "Sparse observations": "观测稀疏",
    "Hard-to-access frontier": "难以抵达的前沿",
    "Mature remote sensing tool": "成熟遥感工具",
    "Highly relevant to Bryan's field": "与 Bryan 的方向高度相关",
    "Powerful but needs GIA correction": "能力强，但需要 GIA 校正",
    "Essential but incomplete": "必要但仍不完整",
    "Important but uncertain": "重要但仍不确定",
    "Useful constraint": "有用约束",
    "Foundational evidence": "基础证据",
    "Key paleo archive": "关键古环境档案",
    "Uncertain but crucial": "不确定但至关重要",
    "Major modeling frontier": "重要建模前沿",
    "High priority": "高优先级",
    "Emerging opportunity": "新兴机会",
    "How does the Antarctic Ice Sheet respond to climate forcing?": "南极冰盖如何响应气候强迫？",
    "The central system linking atmosphere, ocean, ice dynamics, solid Earth, observations, paleoclimate evidence, and future sea-level risk.": "它是连接大气、海洋、冰动力学、固体地球、观测、古气候证据和未来海平面风险的核心系统。",
    "Antarctica and global coastlines": "南极洲与全球海岸线",
    "How does Southern Ocean heat reach ice-shelf cavities?": "南大洋热量如何进入冰架腔体？",
    "Controls basal melting and ice-shelf thinning.": "控制基底融化和冰架变薄。",
    "How does ice flow accelerate after ice shelves weaken?": "冰架减弱后，冰流如何加速？",
    "Connects local forcing to large-scale ice discharge.": "把局地强迫与大尺度冰排放连接起来。",
    "How do bedrock, heat flow, and rebound affect ice stability?": "基岩、热流和回弹如何影响冰体稳定性？",
    "Sets boundary conditions and feedbacks for ice-sheet retreat.": "为冰盖退缩设定边界条件和反馈。",
    "How do we measure change in such a remote environment?": "我们如何测量如此偏远环境中的变化？",
    "Provides constraints for mechanisms and models.": "为机制和模型提供约束。",
    "What did the AIS do in past warm periods?": "过去暖期中南极冰盖发生了什么？",
    "Extends evidence beyond the short satellite record.": "把证据延伸到较短卫星记录之外。",
    "How much will Antarctica contribute to future sea-level rise?": "南极洲未来会对海平面上升贡献多少？",
    "Connects science to coastal risk.": "把科学问题与海岸风险连接起来。",
    "Choose story": "选择故事",
    "Lens": "视角",
    "Story": "故事",
    "Story beats": "故事节点",
    "Output mode": "输出模式",
    "Interactive": "交互式",
    "Selected scientific storyline": "已选科学故事线",
    "Research-use framing": "科研使用视角",
    "Connected nodes": "已连接节点",
    "Slide-ready chain": "可用于幻灯片的链条",
    "Storyboard table": "故事板表格",
    "Storyboard table (open)": "故事板表格（已展开）",
    "Stage": "阶段",
    "Node": "节点",
    "System / Type": "系统 / 类型",
    "Meaning": "含义",
    "Evidence": "证据",
    "Visual chain": "视觉链条",
    "Speaker note": "讲解备注",
    "Past": "过去",
    "Present": "现在",
    "Future": "未来",
    "Ice Sheet Stability": "冰盖稳定性",
    "Ocean Heat Pathways": "海洋热量通路",
    "Hydrofracture & Ice Cliff Risk": "水力破裂与冰崖风险",
    "Solid Earth Feedbacks": "固体地球反馈",
    "Use the animation as a step-by-step explanation. Each node represents one scientific beat; the right card links the beat to evidence such as satellite observations, ocean data, paleo records, or coupled models.": "可将动画作为逐步讲解使用。每个节点代表一个科学叙事节拍；右侧卡片会把该节拍与卫星观测、海洋数据、古环境记录或耦合模型等证据联系起来。",
    "From ocean heat to ice-sheet retreat, the story emerges through connected mechanisms.": "从海洋热量到冰盖退缩，故事通过相互关联的机制展开。",
    "Ocean access links Southern Ocean change to basal melting and ice-shelf thinning.": "海洋通道把南大洋变化与基底融化和冰架变薄联系起来。",
    "Surface melt, crevasses, and shelf strength govern rapid collapse risk.": "表面融水、裂隙和冰架强度共同控制快速崩塌风险。",
    "The solid Earth is both a correction for observations and an active ice-sheet feedback.": "固体地球既是观测校正项，也是主动影响冰盖的反馈机制。",
    "Past Warm Periods": "过去暖期",
    "Marine-based Ice": "海基冰体",
    "Retreat Episodes": "退缩事件",
    "Model Constraints": "模型约束",
    "Ocean Heat": "海洋热量",
    "Shelf Thinning": "冰架变薄",
    "Grounding Retreat": "接地线退缩",
    "Sea-level Risk": "海平面风险",
    "Forcing Pathways": "强迫通路",
    "Uncertainty Range": "不确定性范围",
    "Shelf Break": "陆架坡折",
    "Warm Intervals": "暖期",
    "Melt Archive": "融化档案",
    "Analog Limits": "类比局限",
    "Cavity Circulation": "冰架腔体环流",
    "Basal Melt": "基底融化",
    "Discharge Signal": "冰排放信号",
    "Wind Shift": "风场变化",
    "Persistent Melt": "持续融化",
    "Observation Need": "观测需求",
    "Collapse Analog": "崩塌类比",
    "Surface Melt": "表面融化",
    "Shelf Breakup": "冰架破裂",
    "Response Lag": "响应滞后",
    "Ponding": "融水塘",
    "Crevasse Fields": "裂隙区",
    "MICI Debate": "MICI 争议",
    "Warming Summers": "夏季变暖",
    "Shelf Collapse": "冰架崩塌",
    "Cliff Exposure": "冰崖暴露",
    "Constraint Need": "约束需求",
    "Ice Load Memory": "冰载记忆",
    "Raised Shores": "抬升海岸",
    "Mantle Structure": "地幔结构",
    "Model Input": "模型输入",
    "GRACE Signal": "GRACE 信号",
    "GNSS Uplift": "GNSS 隆升",
    "GIA Correction": "GIA 校正",
    "Grounding Feedback": "接地线反馈",
    "Bedrock Uplift": "基岩隆升",
    "Relative Sea Level": "相对海平面",
    "3D Earth Structure": "三维地球结构",
    "Coupled Projection": "耦合预测",
    "Paleo": "古环境",
    "Model": "模型",
    "Impact": "影响",
    "Forcing": "强迫",
    "Risk": "风险",
    "Feedback": "反馈",
    "Hydrology": "水文",
    "Fracture": "裂隙",
    "Instability": "不稳定性",
    "Atmosphere": "大气",
}
_CODE_PATTERNS = (
    "function ",
    "window.",
    "document.",
    "addEventListener",
    "QWebChannel",
    "__focusResearchUniverse",
)


def current_locale():
    env_locale = os.environ.get("ATLAS_LOCALE")
    if env_locale:
        return env_locale.lower()
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return (data.get("locale") or _DEFAULT_LOCALE).lower()
    except Exception:
        return _DEFAULT_LOCALE


def set_locale(locale_name):
    locale = (locale_name or _DEFAULT_LOCALE).lower()
    if locale not in {"en", "zh"}:
        locale = _DEFAULT_LOCALE
    os.environ["ATLAS_LOCALE"] = locale
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        current = {}
        if _CONFIG_PATH.exists():
            current = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        current["locale"] = locale
        _CONFIG_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        import sys
        print(f"[Antarctic Atlas] Could not persist language setting to {_CONFIG_PATH}", file=sys.stderr)
        pass
    return locale


def _load_locale(locale_name):
    locale = (locale_name or _DEFAULT_LOCALE).lower()
    if locale in _CACHE:
        return _CACHE[locale]
    path = _LOCALE_DIR / f"{locale}.json"
    if not path.exists():
        path = _LOCALE_DIR / f"{_DEFAULT_LOCALE}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    _CACHE[locale] = data
    return data


def t(key, default="", **kwargs):
    text = _load_locale(current_locale()).get(key, default)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def is_chinese_locale():
    return current_locale().startswith("zh")


def _load_exact_map():
    global _EXACT_CACHE
    if _EXACT_CACHE is not None:
        return _EXACT_CACHE
    path = _LOCALE_DIR / "zh_auto.json"
    try:
        _EXACT_CACHE = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _EXACT_CACHE = {}
    return _EXACT_CACHE


def translate_text(text):
    if not is_chinese_locale() or not isinstance(text, str) or not text:
        return text
    if any(pattern in text for pattern in _CODE_PATTERNS) or re.search(r"(^|[;\n{])\s*(const|let|var)\s+\w+\s*=", text):
        return text
    exact = _load_exact_map()
    masks = {}
    masked_text = text
    for index, term in enumerate(_PROTECTED_TERMS):
        token = f"__ATLAS_TERM_{index}__"
        if term in masked_text:
            masked_text = masked_text.replace(term, token)
            masks[token] = term
    if masked_text in _MANUAL_ZH:
        return _restore_protected_terms(_clean_translation(_MANUAL_ZH[masked_text]), masks)
    if text in exact:
        return _restore_protected_terms(_clean_translation(exact[text]), masks)
    if masked_text in exact:
        return _restore_protected_terms(_clean_translation(exact[masked_text]), masks)
    stripped = masked_text.strip()
    if stripped in exact:
        translated = masked_text.replace(stripped, exact[stripped], 1)
        return _restore_protected_terms(_clean_translation(translated), masks)
    if " -> " in masked_text:
        translated = " -> ".join(translate_text(part) for part in masked_text.split(" -> "))
        return _restore_protected_terms(_clean_translation(translated), masks)
    if "Synthesis: For " in masked_text:
        return _restore_protected_terms(_clean_translation(masked_text), masks)
    if ": " in masked_text:
        head, tail = masked_text.split(": ", 1)
        translated_head = _MANUAL_ZH.get(head, exact.get(head, head))
        translated_tail = exact.get(tail, tail)
        if translated_head != head or translated_tail != tail:
            return _restore_protected_terms(_clean_translation(f"{translated_head}: {translated_tail}"), masks)
    return _restore_protected_terms(_clean_translation(masked_text), masks)


def _restore_protected_terms(text, masks):
    for token, term in masks.items():
        text = text.replace(token, term)
    return _clean_translation(text)


def _clean_translation(text):
    if not isinstance(text, str):
        return text
    for bad, good in _TERM_FIXES.items():
        text = text.replace(bad, good)
    text = text.replace("Synthesis: For ", "综合判断：对于 ")
    text = text.replace("Synthesis:", "综合判断：")
    text = text.replace("综合判断:", "综合判断：")
    text = text.replace(" these layers support the theme: ", "，这些图层共同支撑这一主题：")
    text = text.replace(", these layers support the theme: ", "，这些图层共同支撑这一主题：")
    text = text.replace("Measures:", "测量内容：")
    text = text.replace("Observed:", "观测结果：")
    text = text.replace("Region:", "区域：")
    text = text.replace("Type:", "类型：")
    text = text.replace("Main theme:", "核心主题：")
    text = text.replace(",，", "，")
    text = re.sub(r"\bOpenAI\s+API\b", "OpenAI API", text)
    text = re.sub(r"\bDeepSeek\s+API\b", "DeepSeek API", text)
    text = re.sub(r"\bLocal\s+Ollama\b", "本地 Ollama", text)
    text = re.sub(r"AI\s*模块", "AI 模块", text)
    return text


def translate_html(html_text):
    if not is_chinese_locale() or not isinstance(html_text, str) or not html_text:
        return html_text
    exact = _load_exact_map()
    if html_text in exact and "<script" not in html_text.lower() and "<style" not in html_text.lower():
        return _clean_translation(exact[html_text])
    pieces = re.split(r"(<[^>]+>)", html_text)
    output = []
    in_script = False
    in_style = False
    for piece in pieces:
        lower = piece.lower()
        if lower.startswith("<script"):
            in_script = True
            output.append(piece)
            continue
        if lower.startswith("</script"):
            in_script = False
            output.append(piece)
            continue
        if lower.startswith("<style"):
            in_style = True
            output.append(piece)
            continue
        if lower.startswith("</style"):
            in_style = False
            output.append(piece)
            continue
        if piece.startswith("<") or in_script or in_style:
            output.append(piece)
        else:
            output.append(translate_text(piece))
    return "".join(output)


def combo_current_key(combo):
    data = combo.currentData() if combo is not None else None
    return data if isinstance(data, str) and data else combo.currentText()


def add_combo_items(combo, items):
    for item in items:
        combo.addItem(translate_text(item), item)


def set_combo_items(combo, items):
    combo.clear()
    add_combo_items(combo, items)


def localize_structure(value):
    if not is_chinese_locale():
        return value
    if isinstance(value, str):
        return translate_text(value)
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = localize_structure(item)
        return value
    if isinstance(value, tuple):
        return tuple(localize_structure(item) for item in value)
    if isinstance(value, dict):
        for key in list(value.keys()):
            value[key] = localize_structure(value[key])
        return value
    return value


def localize_runtime_globals(namespace):
    if _ORIGINALS_MARKER not in namespace:
        namespace[_ORIGINALS_MARKER] = {}
        for name in (
            "APP_TITLE",
            "UNIVERSE_TOPIC_DETAILS",
            "RESEARCH_AREAS",
            "DIRECTION_DATA",
            "DIRECTION_REGION_COORDS",
            "SYSTEM_LAYERS",
            "SYSTEM_CASES",
            "SYSTEM_PROCESSES",
        ):
            if name in namespace:
                namespace[_ORIGINALS_MARKER][name] = deepcopy(namespace[name])
    originals = namespace.get(_ORIGINALS_MARKER, {})
    for name, value in originals.items():
        namespace[name] = deepcopy(value)
    namespace[_LOCALIZED_MARKER] = False
    if not is_chinese_locale():
        return
    for name in (
        "APP_TITLE",
        "UNIVERSE_TOPIC_DETAILS",
        "RESEARCH_AREAS",
        "DIRECTION_DATA",
        "DIRECTION_REGION_COORDS",
        "SYSTEM_LAYERS",
        "SYSTEM_CASES",
        "SYSTEM_PROCESSES",
    ):
        if name in namespace:
            namespace[name] = localize_structure(namespace[name])
    namespace[_LOCALIZED_MARKER] = True


def localize_widget_tree(root):
    if not is_chinese_locale() or root is None:
        return root
    try:
        from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QLineEdit, QListWidget, QTextBrowser, QTreeWidget, QWidget
    except Exception:
        return root

    widgets = [root]
    if hasattr(root, "findChildren"):
        widgets.extend(root.findChildren(QWidget))

    for widget in widgets:
        if isinstance(widget, QLabel):
            widget.setText(translate_text(widget.text()))
        elif isinstance(widget, QAbstractButton):
            widget.setText(translate_text(widget.text()))
        elif isinstance(widget, QLineEdit):
            widget.setPlaceholderText(translate_text(widget.placeholderText()))
        elif isinstance(widget, QComboBox):
            for index in range(widget.count()):
                if widget.itemData(index) is None:
                    widget.setItemData(index, widget.itemText(index))
                widget.setItemText(index, translate_text(widget.itemText(index)))
        elif isinstance(widget, QListWidget):
            for index in range(widget.count()):
                item = widget.item(index)
                item.setText(translate_text(item.text()))
        elif isinstance(widget, QTreeWidget):
            for column in range(widget.columnCount()):
                header = widget.headerItem()
                if header:
                    header.setText(column, translate_text(header.text(column)))
            for index in range(widget.topLevelItemCount()):
                _localize_tree_item(widget.topLevelItem(index))
        elif isinstance(widget, QTextBrowser):
            plain = widget.toPlainText()
            translated = translate_text(plain)
            if translated != plain:
                widget.setPlainText(translated)
    return root


def _localize_tree_item(item):
    for column in range(item.columnCount()):
        item.setText(column, translate_text(item.text(column)))
    for index in range(item.childCount()):
        _localize_tree_item(item.child(index))


def install_qt_i18n_hooks():
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return
    try:
        from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QTextBrowser
        from PySide6.QtGui import QPainter
    except Exception:
        return

    original_label_set_text = QLabel.setText
    original_button_set_text = QAbstractButton.setText
    original_browser_set_html = QTextBrowser.setHtml
    original_browser_set_plain_text = QTextBrowser.setPlainText
    original_painter_draw_text = QPainter.drawText
    original_combo_add_item = QComboBox.addItem
    original_combo_add_items = QComboBox.addItems

    def label_set_text(self, text):
        return original_label_set_text(self, translate_text(text))

    def button_set_text(self, text):
        return original_button_set_text(self, translate_text(text))

    def browser_set_html(self, text):
        return original_browser_set_html(self, translate_html(text))

    def browser_set_plain_text(self, text):
        return original_browser_set_plain_text(self, translate_text(text))

    def painter_draw_text(self, *args):
        if args and isinstance(args[-1], str):
            args = (*args[:-1], translate_text(args[-1]))
        return original_painter_draw_text(self, *args)

    def combo_add_item(self, *args):
        if not args:
            return original_combo_add_item(self, *args)
        if isinstance(args[0], str):
            text = args[0]
            user_data = args[1] if len(args) > 1 else text
            return original_combo_add_item(self, translate_text(text), user_data)
        if len(args) >= 2 and isinstance(args[1], str):
            icon, text = args[0], args[1]
            user_data = args[2] if len(args) > 2 else text
            return original_combo_add_item(self, icon, translate_text(text), user_data)
        return original_combo_add_item(self, *args)

    def combo_add_items(self, texts):
        for text in texts:
            combo_add_item(self, text)

    QLabel.setText = label_set_text
    QAbstractButton.setText = button_set_text
    QTextBrowser.setHtml = browser_set_html
    QTextBrowser.setPlainText = browser_set_plain_text
    QPainter.drawText = painter_draw_text
    QComboBox.addItem = combo_add_item
    QComboBox.addItems = combo_add_items
    _HOOKS_INSTALLED = True
