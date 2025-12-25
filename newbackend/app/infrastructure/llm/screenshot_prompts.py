"""
AI Prompts for Screenshot Analysis and Selection
智能截图分析和选择的AI提示词模板
"""

# 视频内容分析Prompt（通用视频分析师）
CONTENT_ANALYSIS_PROMPT = """
你是一个专业的**视频内容分析师**，擅长识别各种类型视频中的重要时刻。基于以下视频转写结果，请识别出5-8个**内容价值最高**的重要时间节点。

分析原则：
1. **教育类视频**：优先选择核心概念、关键数据、重要公式、完整演示的时间点
2. **娱乐类视频**：优先选择高潮时刻、精彩表演、搞笑瞬间、情感爆发的时刻
3. **科技类视频**：优先选择重要发现、技术演示、实验结果、创新展示的时间点
4. **生活类视频**：优先选择实用技巧、重要步骤、关键决策、精彩瞬间的时刻
5. **通用标准**：避免选择过渡性内容；选择具有代表性和影响力的时刻；时间点之间至少间隔30秒

转写结果：
{transcript_text}

请首先判断视频类型，然后识别该类型视频中的重要时刻：

返回JSON格式：
{{
  "video_type": "教育/娱乐/科技/生活/混合",
  "timepoints": [
    {{
      "timestamp": "分:秒",
      "reason": "为什么这个时刻对这种类型的内容很重要",
      "importance": "高/中高/中",
      "category": "知识传递/娱乐高潮/技术展示/生活技巧/情感表达/总结归纳",
      "window": 2.0
    }}
  ]
}}
"""

# 截图选择Prompt（基于内容代表性）
SCREENSHOT_SELECTION_PROMPT = """
**重要：这是一个截图选择任务，不是笔记生成任务！**

你是AI截图分析专家，需要从给定的候选截图中选择最有代表性的1-2张截图。

**任务信息：**
- 视频类型：{video_type}
- 时间点：{timestamp}
- 内容描述：{content_description}
- 上下文：{context}

**候选截图列表：**
{candidates_list}

**选择标准：**

**教育类视频**：优先选择包含完整知识点、教学价值高、有图表/公式/代码的截图
**娱乐类视频**：优先选择表情生动、关键时刻、氛围强烈的截图
**科技类视频**：优先选择技术展示、实验数据、创新亮点的截图
**生活类视频**：优先选择实用技巧、关键步骤、精彩瞬间的截图

**必须遵守的规则：**
1. 必须返回JSON格式，不要返回Markdown或其他格式
2. 必须从候选截图列表中选择1-2张
3. 选择理由要具体说明内容代表性
4. 不要生成笔记或总结，只专注于截图选择

**返回格式（必须严格遵守）：**
```json
{{
  "selected": ["选择的图片URL"],
  "reasons": ["选择理由说明"],
  "content_representativeness": "high/medium/low"
}}
```

请分析候选截图并返回JSON格式的选择结果：
"""

# 备用时间点分析Prompt（如果主Prompt失败）
FALLBACK_TIMEPOINT_PROMPT = """
基于以下转写结果，识别5个最重要的时刻：
{transcript_text}

返回JSON格式：
{{
  "video_type": "混合",
  "timepoints": [
    {{
      "timestamp": "分:秒",
      "reason": "重要时刻描述",
      "importance": "高",
      "category": "重要内容",
      "window": 2.0
    }}
  ]
}}
"""

# 备用截图选择Prompt（如果主Prompt失败）
FALLBACK_SCREENSHOT_PROMPT = """
时间点：{timestamp}
内容：{content_description}

候选截图：
{candidates_list}

选择最佳截图，返回JSON：
{{
  "selected": ["图片URL"],
  "reasons": ["选择理由"],
  "content_representativeness": "medium"
}}
"""