"""学情反馈的六级固定规则。"""


FEEDBACK_OPTIONS: dict[int, dict[str, str]] = {
    1: {"emoji": "😵", "label": "完全没有理解"},
    2: {"emoji": "😟", "label": "理解程度较低"},
    3: {"emoji": "😕", "label": "部分理解"},
    4: {"emoji": "😐", "label": "基本理解"},
    5: {"emoji": "🙂", "label": "理解程度较好"},
    6: {"emoji": "😄", "label": "完全理解"},
}


def get_feedback_option(score: int) -> dict[str, str]:
    """根据分数取得对应表情和理解程度文字。"""

    return FEEDBACK_OPTIONS[score]
