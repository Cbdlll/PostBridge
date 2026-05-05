# -*- coding: utf-8 -*-
"""
Doubao Client - 豆包SeeDance视频生成API客户端
API文档: https://doubao.apifox.cn/265914813e0
火山方舟平台: https://ark.cn-beijing.volces.com
"""
import os
import time
import requests
from typing import Optional
from pathlib import Path
from .video_client import VideoClient, VideoGenerationError


class DoubaoClient(VideoClient):
    """
    豆包SeeDance视频生成客户端
    字节跳动火山方舟平台文生视频服务
    
    特点：
    - 支持音画同步，原生声音生成
    - 1080P高清视频生成能力
    - 影视级叙事张力
    """
    
    def __init__(
        self, 
        api_key: str = None,
        base_url: str = None,
        output_dir: str = None,
        model: str = None,
        timeout: int = 300
    ):
        """
        初始化豆包客户端
        
        Args:
            api_key: 火山方舟API Key (环境变量: DOUBAO_API_KEY)
            base_url: API基础地址 (默认: https://ark.cn-beijing.volces.com)
            output_dir: 视频输出目录
            model: 模型ID (doubao-seedance-1-5-pro-251215 或 doubao-seedance-1-0-pro-250528)
            timeout: 请求超时时间(秒)
        """
        super().__init__(api_key=api_key, base_url=base_url, output_dir=output_dir, timeout=timeout)
        
        # 优先级: 参数 > 环境变量 > 默认值
        self.api_key = api_key or os.getenv("DOUBAO_API_KEY", "")
        self.base_url = (base_url or os.getenv("DOUBAO_API_BASE_URL", "https://ark.cn-beijing.volces.com")).rstrip("/")
        self.model = model or "doubao-seedance-1-5-pro-251215"
        
        # 固定参数 - 根据用户需求
        self.resolution = "720p"
        self.ratio = "16:9"
        self.duration = 12
        self.enable_audio = True  # 需要声音
        
        if not self.api_key:
            print("⚠️  警告: 未配置DOUBAO_API_KEY,请在环境变量或参数中设置")
    
    def _get_headers(self) -> dict:
        """获取请求头(Bearer Token认证)"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_prompt(self, prompt: str) -> str:
        """
        构建豆包API的提示词格式
        豆包API支持在prompt中加入参数指令
        
        格式: {原始提示词} --ratio {比例} --fps {帧率} --dur {时长}
        """
        # 根据API文档，将参数附加到prompt中
        # 720p 对应分辨率，16:9是比例，12秒是时长
        # FPS 24是常用帧率
        fps = 24
        return f"{prompt} --ratio {self.ratio} --fps {fps} --dur {self.duration}"
    
    def generate_video(self, prompt: str, **kwargs) -> dict:
        """
        调用豆包API生成视频
        
        Args:
            prompt: 视频生成提示词
            **kwargs: 其他参数(model等)
            
        Returns:
            {
                "task_id": "任务ID",
                "status": "pending",
                "video_url": None,
                "local_path": None
            }
        """
        # 允许临时覆盖模型
        video_model = kwargs.get('model', self.model)
        
        # 构建API请求payload
        payload = {
            "model": video_model,
            "content": [
                {
                    "type": "text",
                    "text": self._build_prompt(prompt)
                }
            ]
        }
        
        try:
            print(f"🎬 [豆包] 开始创建视频生成任务...")
            print(f"   模型: {video_model}")
            print(f"   提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            print(f"   参数: {self.resolution} {self.ratio} {self.duration}秒 音频:{self.enable_audio}")
            
            response = requests.post(
                f"{self.base_url}/api/v3/contents/generations/tasks",
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            # 获取任务ID
            task_id = data.get("id") or data.get("task_id") or data.get("request_id")
            
            if not task_id:
                raise VideoGenerationError(f"API响应缺少task_id: {data}")
            
            print(f"✅ [豆包] 任务创建成功: {task_id}")
            
            return {
                "task_id": task_id,
                "status": "pending",
                "video_url": None,
                "local_path": None,
                "_raw_response": data
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {e.response.text[:200]}"
            
            raise VideoGenerationError(f"豆包API调用失败 - {error_msg}") from e
        
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"网络请求失败: {e}") from e
    
    def check_status(self, task_id: str) -> dict:
        """
        检查豆包视频生成状态
        
        查询接口需要根据实际API文档调整
        
        Returns:
            {
                "status": "pending/processing/completed/failed",
                "video_url": "视频URL(完成后)",
                "progress": 进度百分比(可选)
            }
        """
        try:
            # 根据豆包API文档，状态查询接口
            response = requests.get(
                f"{self.base_url}/api/v3/contents/generations/tasks/{task_id}",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 根据实际API响应调整字段映射
            status = data.get("status", "unknown")
            video_url = data.get("video_url") or data.get("url") or data.get("output_url")
            
            # 若API返回结果列表，取第一个
            if isinstance(data.get("results"), list) and len(data["results"]) > 0:
                video_url = data["results"][0].get("url") or data["results"][0].get("video_url")
            
            return {
                "status": status,
                "video_url": video_url,
                "progress": data.get("progress"),
                "_raw_response": data
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise VideoGenerationError(f"任务不存在: {task_id}") from e
            raise VideoGenerationError(f"状态查询失败: {e}") from e
        
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"网络请求失败: {e}") from e
    
    def wait_for_completion(
        self, 
        task_id: str, 
        max_polls: int = 30,  # 最多轮询30次
        poll_interval: int = 60  # 每60秒查询一次
    ) -> dict:
        """
        轮询等待视频生成完成
        
        Args:
            task_id: 任务ID
            max_polls: 最大轮询次数(默认30次,总计30分钟)
            poll_interval: 轮询间隔(秒,默认60秒)
            
        Returns:
            {
                "status": "completed",
                "video_url": "视频URL"
            }
            
        Raises:
            VideoGenerationError: 生成失败或超时
        """
        # 首次等待3分钟再开始轮询
        initial_wait = 180  # 3分钟
        print(f"⌛ [豆包] 等待视频生成（初始延迟 {initial_wait//60} 分钟）...")
        print(f"   任务ID: {task_id}")
        time.sleep(initial_wait)
        
        print(f"⏳ [豆包] 开始轮询任务状态")
        print(f"   轮询间隔: {poll_interval}秒")
        print(f"   最大轮询次数: {max_polls}")
        print(f"   预计最大等待时间: {initial_wait//60}分钟 + {max_polls * poll_interval//60}分钟")
        
        for attempt in range(max_polls):
            try:
                result = self.check_status(task_id)
                status = result.get("status", "").lower()
                
                print(f"  [{attempt+1}/{max_polls}] 状态: {status}", end="")
                if result.get("progress"):
                    print(f" ({result['progress']}%)", end="")
                print()
                
                # 完成状态
                if status in ["completed", "success", "succeeded", "finished"]:
                    video_url = result.get("video_url")
                    if not video_url:
                        raise VideoGenerationError("视频生成完成但未返回URL")
                    
                    print(f"✅ [豆包] 视频生成完成")
                    print(f"   URL: {video_url[:80]}{'...' if len(video_url) > 80 else ''}")
                    
                    return {
                        "status": "completed",
                        "video_url": video_url,
                        "task_id": task_id
                    }
                
                # 失败状态
                elif status in ["failed", "error", "fail"]:
                    error_msg = result.get("error") or result.get("message") or "未知错误"
                    raise VideoGenerationError(f"视频生成失败: {error_msg}")
                
                # 处理中,继续等待
                elif status in ["pending", "processing", "running", "queued", "waiting"]:
                    if attempt < max_polls - 1:
                        time.sleep(poll_interval)
                    continue
                
                else:
                    print(f"⚠️  未知状态: {status},继续轮询...")
                    if attempt < max_polls - 1:
                        time.sleep(poll_interval)
                
            except VideoGenerationError:
                raise
            except Exception as e:
                print(f"⚠️  查询状态异常: {e}")
                if attempt < max_polls - 1:
                    time.sleep(poll_interval)
                else:
                    raise VideoGenerationError(f"状态查询失败: {e}") from e
        
        # 超时
        raise VideoGenerationError(
            f"视频生成超时 (已等待{max_polls * poll_interval}秒), "
            f"任务ID: {task_id}, 请稍后手动查询或联系服务商"
        )
