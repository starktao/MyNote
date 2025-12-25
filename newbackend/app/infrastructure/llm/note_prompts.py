"""
笔记生成的 Prompt 模板
包含视频类型模板和笔记风格模板
"""

# 视频类型模板
VIDEO_TYPE_TEMPLATES = {
    "tech": """
## 视频类型重点（技术/教程）
- 仅依转写提炼核心概念、公式、代码、命令或参数；禁止杜撰结构
- 若出现实验/演示，说明输入、环境、依赖、产出，以及提到的错误/解决方案
- 出现的代码或命令使用 fenced code block 保留原样
- 结尾写"总结/记忆提示"：只能引用原文中的比喻、案例或讲者的记忆方法；若原文未提供，就总结实际强调的核心结论
""",

    "dialogue": """
## 视频类型重点（人物对话）
- 严格根据转写区分说话者、提问/回答、观点与证据；不可添加未出现的角色或内容
- 可用"人物→观点/引语"或对照表呈现，记录清晰的共识/分歧
- 结尾写"对话总结"：概括主要结论、共识/分歧、明确的行动或金句
""",

    "science": """
## 视频类型重点（科普/解读）
- 依转写内容整理"现象/事件→解释→数据/证据→影响/风险"，缺项则跳过
- 标注提到的证据来源、数据、不确定性或争议
- 结尾提供"总结/记忆提示"：引用原文中的类比/比喻/启示，或重申实际提到的关键影响
""",

    "review": """
## 视频类型重点（测评/选型）
- 依据转写提取评测维度、参数、优缺点、结论、推荐理由；不得臆造
- 若有对比或配置建议，用列表或对照表呈现；没有则跳过
- 结尾写"测评总结与建议"：概括最终推荐、适用场景、注意事项或预算提醒
"""
}

# 笔记风格模板
STYLE_TEMPLATES = {
    "concise": """
## 笔记风格（精简）
- 仅保留最核心要点，每个要点 1-2 句，用短列表；无多余解释
- 如果转写中出现时间戳/步骤，可附在要点后；没有就不要补写
""",

    "detailed": """
## 笔记风格（详细）
- 充分展开每个知识点：背景、推理、示例、限制条件均照转写保留
- 允许长段落或嵌套列表，引用原话帮助理解，但不得杜撰
""",

    "teaching": """
## 笔记风格（教学）
- 用讲义式语气整理：突出学习目标、关键概念、步骤、常见误区/提醒
- 可加入"提示/注意/练习"标签，但内容必须源自转写
""",

    "xiaohongshu": """
## 笔记风格（小红书）
- 语言轻松、有记忆点，可用表情符号或"Tip/踩坑"等提示，但信息必须准确
- 突出亮点与踩坑经验，结尾用"总结/种草/拔草"口吻重申重点，前提是原文提到
"""
}

# 类型标签映射（用于日志和前端显示）
VIDEO_TYPE_LABELS = {
    "tech": "技术/教程",
    "dialogue": "人物对话",
    "science": "科普/解读",
    "review": "测评/选型"
}

STYLE_LABELS = {
    "concise": "精简",
    "detailed": "详细",
    "teaching": "教学",
    "xiaohongshu": "小红书"
}


def get_video_type_prompt(video_type: str) -> str:
    """
    获取视频类型的 Prompt 片段

    Args:
        video_type: 视频类型 (tech/dialogue/science/review)

    Returns:
        对应的 Prompt 模板文本
    """
    video_type = (video_type or "science").lower()
    return VIDEO_TYPE_TEMPLATES.get(video_type, VIDEO_TYPE_TEMPLATES["science"])


def get_style_prompt(note_style: str) -> str:
    """
    获取笔记风格的 Prompt 片段

    Args:
        note_style: 笔记风格 (concise/detailed/teaching/xiaohongshu)

    Returns:
        对应的 Prompt 模板文本
    """
    note_style = (note_style or "detailed").lower()
    return STYLE_TEMPLATES.get(note_style, STYLE_TEMPLATES["detailed"])
