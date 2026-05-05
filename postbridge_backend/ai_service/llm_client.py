# -*- coding: utf-8 -*-
"""
LLM Client - 统一的大语言模型调用接口
支持 OpenAI 兼容 API（如 OpenAI, DeepSeek, Claude via proxy 等）
支持 Mock 模式用于测试和演示
"""
import os
import requests
from typing import Optional, Generator


# ============== Mock 数据（基于真实终端输出） ==============
MOCK_RESPONSES = {
    "红薯": '''[
  {
    "title": "一刀切开，热气腾腾的金黄红薯，瞬间点燃味蕾！",
    "video_prompt": "清晨柔和的自然光洒在金黄的红薯田，农民挥动镰刀快速收割，手中满载新鲜红薯。镜头快速拉近到一只手把红薯从泥土中拔起，土壤颗粒飞溅，红薯表面呈现露珠光泽。随后刀锋精准切开红薯，内部绵软的金黄肉质瞬间冒出热气，蒸汽在阳光下形成细腻的光环。镜头转向手把热气吹向镜头，观众仿佛闻到甜香。整个画面保持真实田间色调，背景是绿油油的叶子和远处的山影，声音配合刀切声与轻快的节奏鼓点。",
    "tags": ["红薯", "农产品", "抖音种草", "快速下单"],
    "description": "看到热气了吗？快在评论里告诉我你最想配的酱料，私信我立刻下单送到家，限时特惠等你抢！"
  },
  {
    "title": "从田间到餐桌，红薯甜品秒变网红美味！",
    "video_prompt": "午后金色阳光透过稻草棚洒在农家小院，农妇手提装满红薯的竹篮走向厨房。镜头跟随红薯被放进木质砧板，快速切片，随后镜头切换到厨房灶台，红薯片在锅中翻炒，糖浆滴落，表面形成亮丽的焦糖光泽。接着镜头俯拍，一个透明玻璃杯里层层叠加烤红薯块、奶油、坚果和薄荷叶，光影在杯壁上跳动，呈现诱人的层次感。最后镜头拉回到餐桌，手轻轻舀起一勺，红薯块软糯弹牙，光滑的奶油在阳光下闪光，背景是绿植和温暖的木质家具，整个画面保持自然光照，无任何文字装饰。",
    "tags": ["红薯甜品", "厨房实拍", "抖音美食", "冲动购买"],
    "description": "想尝试这款红薯甜品吗？点赞并在评论里说出你的创意配料，私信下单即送精美包装，先到先得！"
  },
  {
    "title": "红薯苗萌发瞬间，种下健康，收获丰收！",
    "video_prompt": "清晨微雾笼罩的农田，柔和的晨光照在一排排整齐的红薯苗床上。农夫手捧装有红薯芽的透明塑料盒，轻轻将芽移植到预先挖好的细小坑位，手指轻触土壤，泥土微微翻起。镜头特写红薯芽的嫩绿叶尖，露珠在叶面闪烁，随后快速转场显示时间流逝的快进效果：苗床里的红薯苗快速抽枝长叶，阳光逐渐加强，虫鸣声与轻快的背景音乐同步。最后镜头定格在成熟的红薯田，红薯饱满，农夫笑着举起一只大红薯，阳光在红薯表面形成温暖的光晕，背景是蓝天白云和远处的山峦，画面真实自然，未出现任何文字。",
    "tags": ["红薯种植", "农业科技", "抖音生活", "种植赚钱"],
    "description": "想在自家院子里种红薯吗？快在评论区留言你的种植计划，私信获取种植套装优惠，限量送达！"
  }
]'''
}


class LLMClient:
    """
    LLM 客户端，通过 base_url 和 api_key 调用 OpenAI 兼容接口
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model: str = "gpt-4o",
        timeout: int = 600,  # 默认超时 10 分钟（600 秒）
        max_retries: int = 3  # 重试次数
    ):
        """
        初始化 LLM 客户端
        
        Args:
            base_url: API 基础地址（如 https://api.openai.com/v1）
            api_key: API 密钥
            model: 模型名称
            timeout: 请求超时时间（秒），默认 600 秒（10 分钟）
            max_retries: 最大重试次数，默认 3 次
        """
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(
        self,
        user_message: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        发送聊天请求并返回完整响应（带重试机制）
        支持 Mock 模式：当 api_key 为 "mock" 时返回预设数据
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            temperature: 随机性控制 (0-2)
            max_tokens: 最大生成 token 数
            
        Returns:
            模型生成的文本
        """
        import time
        
        # Mock 模式：检测主题并返回预设数据
        if self.api_key.lower() == "mock":
            print(f"  [LLM] Mock 模式已启用")
            for topic_key in MOCK_RESPONSES.keys():
                if topic_key in user_message:
                    print(f"  [LLM] 匹配到 Mock 主题: {topic_key}")
                    return MOCK_RESPONSES[topic_key]
            # 未匹配到预设主题，返回通用mock数据
            print(f"  [LLM] 未匹配到预设主题，返回通用 Mock 数据")
            return '''[{"title": "Mock视频", "video_prompt": "这是一个Mock示例视频", "tags": ["mock"], "description": "Mock描述"}]'''
        
        # 正常模式：发送真实请求
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                print(f"  [LLM] 请求中... (尝试 {attempt + 1}/{self.max_retries})")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout as e:
                last_error = e
                wait_time = (attempt + 1) * 10  # 指数退避: 10, 20, 30 秒
                print(f"  ⚠️ LLM 请求超时, {wait_time} 秒后重试...")
                time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"  ⚠️ LLM 请求失败: {e}, {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    break
        
        raise RuntimeError(f"LLM 请求失败 (已重试 {self.max_retries} 次): {last_error}") from last_error

    def chat_stream(
        self,
        user_message: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[str, None, None]:
        """
        流式聊天请求，逐步返回生成内容
        
        Yields:
            生成的文本片段
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM 流式请求失败: {e}") from e


# ============== Prompt Engineering ==============

# 视频 Prompt 生成的系统提示词
VIDEO_PROMPT_SYSTEM = """
# Role
你是一位资深互联网带货操盘手和AI营销视频专家,深谙短视频平台的底层流量逻辑和用户消费心理,擅长通过精准的视觉描述打造"黄金3秒"获客视频。

# Goal
根据用户提供的【产品/主题】、【目标平台】和【风格要求】,设计能直接带来询单和转化的AI视频提示词方案。

# Constraints
1. **语言严格要求**: 所有字段(包括 title, description, tags, video_prompt) **必须完全使用中文**。
2. **Video Prompt 结构与规范** (严格按照以下顺序构建单一具体段落, 200字以内):
   - **主要动作**: 以一句话核心动作直接开始 (e.g., "一位中国农民微笑着展示红薯..."), 拒绝废话前言。
   - **动作细节**: 描述具体的互动手势、微表情。
   - **外观特征**: **必须是中国面孔** (Chinese face), 具体的衣着、发型 (符合产品调性)。
   - **背景环境**: 具体的中国风真实场景 (如真实田间、中式厨房), 避免虚假影棚感。
   - **镜头运镜**: 指定镜头角度 (特写/推拉/固定) 和移动方式。
   - **光影色彩**: 描述自然光线、真实质感 (Real-life footage, natural lighting)。
   - **动态变化**: 描述画面中的微小变化或突发事件 (如热气升腾、微风吹过)。
   - **单一段落**: 所有视觉描述必须连贯地写在一个段落中, 不要使用列表格式。
3. **内容禁忌**: 
   - 严禁出现任何文字、字幕、标语、广告牌 (AI生成文字不可控且影响观感)。
   - 严禁使用西方人面孔/环境, 必须符合中国受众审美。
4. **输出格式**: 仅输出标准的 JSON 数组, 严禁包含 markdown 代码块标记或其他废话。

# Output Schema (JSON Array)
[
  {
    "title": "吸睛标题(带痛点或利益点,中文,10字以内)",
    "video_prompt": "高度细节化的中文画面提示词(严格遵循7点结构, 单一段落, 200字以内)",
    "tags": ["精准行业词", "流量词", "转化词"],
    "description": "引导互动的视频简介(包含引导私信/评论的钩子,中文)"
  }
]
"""


from .platform_personas import PLATFORM_PERSONAS

def generate_video_prompt(
    client: LLMClient,
    topic: str,
    platform: str = "douyin",
    style: str = "产品展示",
    custom_persona: str = None,
    count: int = 1
) -> list:
    """
    根据主题生成视频提示词 (支持批量生成)
    
    Args:
        client: LLM 客户端实例
        topic: 用户输入的产品/主题
        platform: 目标发布平台 (douyin/xhs/ks/wx)
        style: 视频风格
        custom_persona: 自定义用户画像（可选，优先使用）
        count: 生成数量 (1-5)
        
    Returns:
        包含 title, video_prompt, tags, description 的字典列表
    """
    # 平台名称映射
    platform_name_map = {
        'douyin': '抖音',
        'xhs': '小红书',
        'ks': '快手',
        'wx': '视频号',
        'bilibili': 'B站'
    }
    platform_display_name = platform_name_map.get(platform, platform)
    
    # 获取平台特定画像，优先使用传入的自定义画像，否则查表
    if custom_persona is not None:
        persona = custom_persona
    else:
        persona = PLATFORM_PERSONAS.get(platform, "")

    user_message = f"""
# Task Configuration
- **核心主题**: {topic}
- **发布平台**: {platform_display_name}
- **预设风格**: {style}
- **生成数量**: {count} 个
- **核心目标**: 通过AI短视频实现获客转化

# Platform Persona (平台策略)
{persona}

# Prompt Structure Requirements (必须严格执行)
请为每个视频构思一个独特的场景，并按照以下7点结构编写 `video_prompt` (必须是**单一段落**, 不要分点):
1. **主要动作**: 直接开始描述核心动作。
2. **动作细节**: 补充手势和微表情。
3. **外观特征**: 强调**中国面孔** (Chinese face) 和适宜装束。
4. **背景环境**: 具体的中国本土化场景。
5. **镜头运镜**: 具体的视角控制。
6. **光影色彩**: 真实的自然光感。
7. **动态变化**: 引入环境动态细节。

# Critical Rules
1. **严禁文字**: 画面内不能有任何文字。
2. **单一段落**: Prompt 必须是连贯的一个段落，直接从动作开始 (e.g., "一位..."), 不要写 "镜头开始于..." 或 "视频展示了..."。
3. **真实感**: 避免AI生成的过度磨皮感，追求真实生活质感。

请直接输出 JSON 数组:
"""
    
    print(f"\n[LLM Input Prompt]:\n{user_message}\n")
    
    response = client.chat(
        user_message=user_message,
        system_prompt=VIDEO_PROMPT_SYSTEM,
        temperature=0.8
    )
    
    print(f"\n[LLM Output Response]:\n{response}\n")
    
    # 解析 JSON 响应
    import json
    try:
        # 尝试提取 JSON（处理可能的 markdown 代码块）
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        result = json.loads(response.strip())
        
        # 确保返回的是列表
        if isinstance(result, dict):
            return [result]
        elif isinstance(result, list):
            return result
        else:
            raise ValueError("LLM returned unexpected format")
            
    except Exception as e:
        # 如果解析失败，返回原始响应作为单个结果的fallback
        print(f"JSON Parse Error: {e}, Response: {response}")
        return [{
            "title": topic,
            "video_prompt": response[:500], # Truncate if too long
            "tags": [topic],
            "description": f"关于{topic}的视频 (解析失败兜底)",
            "_raw_response": response,
            "_parse_error": str(e)
        }]
