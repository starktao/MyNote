"""
AI Service - AI Summarization using OpenAI-compatible APIs
"""

from typing import List, Dict, Any, Optional
from datetime import timedelta
import openai
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """Transcript segment model"""
    start: float
    end: float
    text: str


class AISource(BaseModel):
    """AI source data model"""
    title: str
    segments: List[TranscriptSegment]
    tags: List[str] = []
    screenshot: bool = False
    video_img_urls: List[str] = []
    link: bool = False
    formats: List[str] = []
    video_type: Optional[str] = "science"  # tech/dialogue/science/review
    note_style: Optional[str] = "detailed"  # concise/detailed/teaching/xiaohongshu
    extras: Optional[str] = None
    screenshot_density: Optional[str] = "medium"  # low/medium/high


class AIService:
    """Service for AI summarization using OpenAI-compatible APIs"""

    # Prompt templates based on original backend
    BASE_PROMPT = '''# 任务说明
你是专业的视频笔记助手。根据视频转录内容，生成结构化的 Markdown 笔记。

# 视频信息
**标题**: {video_title}
**标签**: {tags}
**时长**: {video_duration}
**时间范围**: 00:00 ~ {max_time}

# 转录内容
以下是视频的完整转录，格式为"时间 - 文本"：

---
{segment_text}
---

# 输出要求

## 1. 格式规范
- 输出纯 Markdown 文本，不要用代码块包裹（❌ 不要用 ```markdown）
- 使用中文撰写，专有名词、技术术语可保留英文
- 标题格式：使用 `## 1. 标题` 而非 `1. **标题**`（避免解析错误）
- 数学公式使用 LaTeX 语法：`$公式$` 或 `$$公式$$`

## 2. 内容处理原则
**必须保留**：
- 核心概念和关键定义
- 重要步骤和操作流程
- 代码示例和演示
- 结论和建议

**必须删除**：
- 开场白和结束语（"大家好"、"今天就到这里"）
- 广告和推广内容
- 填充词和口语化表达
- 重复和冗余内容

## 3. 笔记组织
{video_type_instruction}
{style_instruction}

额外重要的任务如下(每一个都必须严格完成):

'''

    # Format additions
    SCREENSHOT_ADDITION = """
## 4. 截图标记规则

### ⚠️ 硬性约束（必须严格遵守）

1. **时间范围限制**
   - 视频总时长：{video_duration}
   - 所有截图时间必须 ≤ {max_time}
   - 禁止使用超出范围的时间

2. **时间来源限制**
   - 只能从上面"转录内容"中的时间点选择
   - 禁止编造不存在的时间戳
   - 禁止照抄示例中的时间

3. **格式要求**
   - 格式：`*Screenshot-MM:SS`
   - 时间必须两位数：`03:39` 而非 `3:39`
   - 独立成行，前后各留一个空行

### 📸 何时插入截图（选择策略）

**教育类视频** - 在以下位置插入：
- ✅ 重要概念**首次出现**时（如：单例模式的定义）
- ✅ 代码**演示或实现**关键步骤时
- ✅ 图表、架构图、流程图**展示**时
- ✅ 对比**说明**关键差异时（如：饿汉式 vs 懒汉式）
- ✅ 重要公式或算法**讲解**时

**技术类视频** - 在以下位置插入：
- ✅ IDE 中的**代码编写**过程
- ✅ 调试或**运行结果**展示
- ✅ 配置文件或**设置界面**
- ✅ 错误提示和**解决方案**展示

{density_instruction}

**硬性约束**：
- ❌ 不要在开场白和结束语插入
- ❌ 不要连续插入（间隔太近）

### ✅ 正确示例（基于实际转录时间 {example_time}）

```markdown
## 一、单例模式简介
单例模式是一种创建型设计模式...

*Screenshot-{example_time}
```

### ❌ 错误示例（禁止）

```markdown
❌ *Screenshot-12:05  （如果视频只有 11:08，超出范围）
❌ *Screenshot-24:12  （编造的时间，不存在于转录中）
❌ *Screenshot-3:39   （格式错误，应为 03:39）
```

### 🔍 最终检查清单

在生成完笔记后，请自查：
- [ ] 所有时间戳 ≤ {max_time}
- [ ] 所有时间戳存在于转录内容中
- [ ] 格式为 `*Screenshot-MM:SS`
- [ ] 每个标记独立成行
- [ ] 间隔合理（≥ 30秒）

"""

    AI_SUM = """
现在请根据以上要求生成笔记。
"""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        """
        Initialize AI service

        Args:
            api_key: API key for the AI service
            base_url: Base URL for the AI service
            model_name: Model name to use
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        print(f"[AI_SERVICE] Initialized with model: {model_name}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        return str(timedelta(seconds=int(seconds)))[2:]  # e.g., 03:15

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        """Build text from segments"""
        return "\n".join(
            f"{self._format_time(seg.start)} - {seg.text.strip()}"
            for seg in segments
        )

    def _ensure_segments_type(self, segments: List[Any]) -> List[TranscriptSegment]:
        """Ensure all segments are TranscriptSegment objects"""
        result = []
        for seg in segments:
            if isinstance(seg, dict):
                result.append(TranscriptSegment(**seg))
            elif isinstance(seg, TranscriptSegment):
                result.append(seg)
            else:
                # Handle other possible formats
                if hasattr(seg, 'start') and hasattr(seg, 'end') and hasattr(seg, 'text'):
                    result.append(TranscriptSegment(
                        start=float(seg.start),
                        end=float(seg.end),
                        text=str(seg.text)
                    ))
        return result

    def _get_safe_example_time(self, segments: List[TranscriptSegment]) -> str:
        """从转录中选择一个安全的示例时间"""
        if not segments:
            return "03:30"

        # 选择中间附近的某个时间点
        mid_index = len(segments) // 2
        mid_time = segments[mid_index].start
        return self._format_time(mid_time)

    def _get_density_instruction(self, density: str) -> str:
        """
        Generate screenshot density instruction based on user selection

        Args:
            density: 'low', 'medium', or 'high'

        Returns:
            Formatted density instruction text
        """
        density_map = {
            "low": "**数量要求**：\n选取转写中最重要的 1-3 个时间点做截图，保持 ≥30 秒间隔。",
            "medium": "**数量要求**：\n选取 3-5 个关键时间点，覆盖不同阶段，保持 ≥30 秒间隔。",
            "high": "**数量要求**：\n选取 5-8 个时间点，尽量覆盖所有主题，保持 ≥30 秒间隔。"
        }
        return density_map.get(density, density_map["medium"])

    def _get_style_instruction(self) -> str:
        """获取风格指导（已废弃，保留用于兼容）"""
        # 新版本不再使用，由 video_type 和 note_style 替代
        return ""

    def _get_video_type_instruction(self) -> str:
        """获取视频类型指导"""
        from app.infrastructure.llm.note_prompts import get_video_type_prompt
        video_type = getattr(self, 'video_type', 'science')
        return get_video_type_prompt(video_type)

    def _get_note_style_instruction(self) -> str:
        """获取笔记风格指导"""
        from app.infrastructure.llm.note_prompts import get_style_prompt
        note_style = getattr(self, 'note_style', 'detailed')
        return get_style_prompt(note_style)

    def create_messages(self, segments: List[TranscriptSegment], title: str, tags: List[str]) -> List[Dict[str, str]]:
        """Create messages for AI API"""
        # Calculate video duration
        max_segment_time = max(seg.end for seg in segments) if segments else 0
        video_duration = self._format_time(max_segment_time)
        max_time = self._format_time(max_segment_time)

        # Generate safe example time from actual transcript
        example_time = self._get_safe_example_time(segments)

        # Build base content with new prompt structure
        content = self.BASE_PROMPT.format(
            video_title=title,
            video_duration=video_duration,
            max_time=max_time,
            segment_text=self._build_segment_text(segments),
            tags=", ".join(tags) if tags else "无标签",
            video_type_instruction=self._get_video_type_instruction(),
            style_instruction=self._get_note_style_instruction()
        )

        # Add format-specific instructions
        if "screenshot" in self.formats:
            print("[AI_SERVICE] Adding screenshot requirement")
            # 动态生成密度指令
            density_instruction = self._get_density_instruction(
                getattr(self, 'screenshot_density', 'medium')
            )
            content += self.SCREENSHOT_ADDITION.format(
                video_duration=video_duration,
                max_time=max_time,
                example_time=example_time,
                density_instruction=density_instruction
            )

        # Add extras if provided
        if self.extras:
            content += f"\n\n额外要求：\n{self.extras}\n"

        # Add final instruction
        content += self.AI_SUM

        print(f"[AI_SERVICE] Prompt length: {len(content)} characters")
        print(f"[AI_SERVICE] Video duration: {video_duration}, Max time: {max_time}, Example time: {example_time}")

        return [{"role": "user", "content": content}]

    def summarize(self, source: AISource) -> str:
        """
        Generate summary from transcript using AI

        Args:
            source: AISource containing transcript and metadata

        Returns:
            Generated markdown summary
        """
        try:
            print(f"[AI_SERVICE] Starting summarization for: {source.title}")
            print(f"[AI_SERVICE] Model: {self.model_name}")
            print(f"[AI_SERVICE] Video Type: {source.video_type}")
            print(f"[AI_SERVICE] Note Style: {source.note_style}")
            print(f"[AI_SERVICE] Segments: {len(source.segments)}")
            print(f"[AI_SERVICE] Screenshot Density: {source.screenshot_density}")

            # Set format options and new fields
            self.formats = source.formats or []
            self.extras = source.extras
            self.video_type = source.video_type
            self.note_style = source.note_style
            self.screenshot_density = source.screenshot_density  # 保存截图密度

            # Ensure segments are proper type
            source.segments = self._ensure_segments_type(source.segments)

            # Create messages
            messages = self.create_messages(source.segments, source.title, source.tags)

            # Call AI API
            print(f"[AI_SERVICE] Calling AI API...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=8000  # Reasonable limit for most models
            )

            result = response.choices[0].message.content.strip()
            print(f"[AI_SERVICE] AI response received, length: {len(result)} characters")

            return result

        except Exception as e:
            print(f"[AI_SERVICE] Error during summarization: {str(e)}")
            raise Exception(f"AI summarization failed: {str(e)}")

    def test_connection(self) -> bool:
        """Test connection to AI service"""
        try:
            print(f"[AI_SERVICE] Testing connection with model: {self.model_name}")

            # Simple test message
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "你好，请回复\"测试\""}],
                temperature=0.7,
                max_tokens=10
            )

            result = response.choices[0].message.content.strip()
            print(f"[AI_SERVICE] Test response: {result}")

            return True

        except Exception as e:
            print(f"[AI_SERVICE] Connection test failed: {str(e)}")
            return False

    def list_models(self) -> List[str]:
        """List available models"""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            print(f"[AI_SERVICE] Failed to list models: {str(e)}")
            return []
