# -*- coding: utf-8 -*-
"""
Transit2 Client - 中转站2视频生成API客户端
支持 Sora-2, Sora-2-Pro, Kling-video-o1 模型
Base URL: https://api.aiiai.top
API文档: https://gpt-best.apifox.cn/api-358024351 (Sora)
         https://gpt-best.apifox.cn/api-216574019 (可灵)
"""
import os
import time
import requests
from typing import Optional
from pathlib import Path
from .video_client import VideoClient, VideoGenerationError

# 禁用 SSL 警告避免日志刷屏
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Transit2Client(VideoClient):
    """
    中转站2视频生成客户端
    API聚合平台,提供 Sora-2, Sora-2-Pro, Kling 视频生成能力
    """
    
    # Sora 模型列表
    SORA_MODELS = ['sora-2', 'sora-2-pro']
    # 可灵模型列表
    KLING_MODELS = ['kling-video-o1']
    
    def __init__(
        self, 
        api_key: str = None,
        base_url: str = None,
        output_dir: str = None,
        model: str = 'sora-2',
        duration: int = 10,  # Sora默认10秒, Kling默认5秒
        timeout: int = 300
    ):
        """
        初始化中转站2客户端
        
        Args:
            api_key: 中转站2 API Key (环境变量: TRANSIT2_API_KEY)
            base_url: API基础地址 (默认: https://api.aiiai.top)
            output_dir: 视频输出目录
            model: 模型ID (sora-2, sora-2-pro, kling-video-o1)
            duration: 视频时长 (Sora:10/15秒, Kling:5/10秒)
            timeout: 请求超时时间(秒)
        """
        super().__init__(api_key=api_key, base_url=base_url, output_dir=output_dir, timeout=timeout)
        
        # 优先级: 参数 > 环境变量 > 默认值
        self.api_key = api_key or os.getenv("TRANSIT2_API_KEY", "")
        self.base_url = (base_url or os.getenv("TRANSIT2_API_BASE_URL", "https://api.aiiai.top")).rstrip("/")
        # 确保model不为None，使用默认值'sora-2'
        self.model = model if model is not None else 'sora-2'
        self.duration = duration
        # 固定参数: 720p, 9:16
        self.aspect_ratio = "9:16"
        
        # 日志
        print(f"🔧 [Transit2Client] model={self.model}, api_key={'已设置' if self.api_key else '未设置'}")
    
    def _get_headers(self) -> dict:
        """获取请求头(Bearer Token认证)"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _is_kling_model(self) -> bool:
        """判断当前模型是否为可灵"""
        return self.model in self.KLING_MODELS
    
    def _is_sora_model(self) -> bool:
        """判断当前模型是否为Sora"""
        return self.model in self.SORA_MODELS
    
    def generate_video(self, prompt: str, duration: int = None, **kwargs) -> dict:
        """
        调用中转站2 API生成视频
        
        Args:
            prompt: 视频生成提示词
            duration: 视频时长 (Sora:10/15秒, Kling:5/10秒)
            **kwargs: 其他参数
            
        Returns:
            {
                "task_id": "任务ID",
                "status": "pending",
                "video_url": None,
                "local_path": None
            }
        """
        print(f"🔍 [DEBUG] generate_video 调用参数:")
        print(f"   self.model = {self.model}")
        print(f"   kwargs = {kwargs}")
        
        video_duration = duration or self.duration
        video_model = kwargs.get('model', self.model)
        
        print(f"   最终 video_model = {video_model}")
        
        # 根据模型类型选择不同的API端点和参数格式
        if video_model in self.KLING_MODELS:
            return self._generate_kling_video(prompt, video_duration, video_model)
        else:
            return self._generate_sora_video(prompt, video_duration, video_model)
    
    def _generate_sora_video(self, prompt: str, duration: int, model: str) -> dict:
        """调用Sora API生成视频"""
        # Sora 可选时长: 10秒 / 15秒
        if duration not in [10, 15]:
            duration = 10  # 默认10秒
        
        payload = {
            "prompt": prompt,
            "model": model,
            "aspect_ratio": self.aspect_ratio,  # 9:16
            "hd": False,
            "duration": str(duration)
        }
        
        try:
            print(f"🎬 [Transit2-Sora] 开始创建视频生成任务...")
            print(f"   模型: {model}")
            print(f"   提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            print(f"   时长: {duration}秒")
            print(f"   比例: {self.aspect_ratio}")
            
            response = requests.post(
                f"{self.base_url}/v2/videos/generations",
                headers=self._get_headers(),
                json=payload,
                timeout=60,
                verify=False  # 禁用 SSL 验证避免证书问题
            )
            response.raise_for_status()
            data = response.json()
            
            task_id = data.get("task_id") or data.get("id") or data.get("request_id")
            
            if not task_id:
                raise VideoGenerationError(f"API响应缺少task_id: {data}")
            
            print(f"✅ [Transit2-Sora] 任务创建成功: {task_id}")
            
            return {
                "task_id": task_id,
                "status": data.get("status", "pending"),
                "video_url": data.get("video_url") or data.get("url"),
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
            
            raise VideoGenerationError(f"Transit2 Sora API调用失败 - {error_msg}") from e
        
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"网络请求失败: {e}") from e
    
    def _generate_kling_video(self, prompt: str, duration: int, model: str) -> dict:
        """调用可灵API生成视频"""
        # 可灵 可选时长: 5秒 / 10秒
        if duration not in [5, 10]:
            duration = 5  # 默认5秒
        
        payload = {
            "model_name": model,
            "prompt": prompt,
            "aspect_ratio": self.aspect_ratio,  # 9:16
            "duration": str(duration),
            "mode": "std"  # 高性能模式
        }
        
        try:
            print(f"🎬 [Transit2-Kling] 开始创建视频生成任务...")
            print(f"   模型: {model}")
            print(f"   提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            print(f"   时长: {duration}秒")
            print(f"   比例: {self.aspect_ratio}")
            
            response = requests.post(
                f"{self.base_url}/kling/v1/videos/text2video",
                headers=self._get_headers(),
                json=payload,
                timeout=60,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # 可灵API响应格式: {"code": 0, "data": {"task_id": "..."}}
            if data.get("code") != 0:
                raise VideoGenerationError(f"可灵API错误: {data.get('message', '未知错误')}")
            
            task_data = data.get("data", {})
            task_id = task_data.get("task_id") or data.get("request_id")
            
            if not task_id:
                raise VideoGenerationError(f"API响应缺少task_id: {data}")
            
            print(f"✅ [Transit2-Kling] 任务创建成功: {task_id}")
            
            return {
                "task_id": task_id,
                "status": task_data.get("task_status", "pending"),
                "video_url": None,
                "local_path": None,
                "_raw_response": data,
                "_model_type": "kling"
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f": {error_detail}"
            except:
                error_msg += f": {e.response.text[:200]}"
            
            raise VideoGenerationError(f"Transit2 Kling API调用失败 - {error_msg}") from e
        
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"网络请求失败: {e}") from e
    
    def check_status(self, task_id: str, model_type: str = None) -> dict:
        """
        检查视频生成状态
        
        Args:
            task_id: 任务ID
            model_type: 模型类型 ("sora" 或 "kling")
            
        Returns:
            {
                "status": "pending/processing/completed/failed",
                "video_url": "视频URL(完成后)",
                "progress": 进度百分比(可选)
            }
        """
        # 自动检测模型类型
        if model_type is None:
            model_type = "kling" if self._is_kling_model() else "sora"
        
        if model_type == "kling":
            return self._check_kling_status(task_id)
        else:
            return self._check_sora_status(task_id)
    
    def _check_sora_status(self, task_id: str) -> dict:
        """检查Sora任务状态"""
        # 添加重试机制处理 SSL 错误
        max_retries = 3
        for retry in range(max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/v2/videos/generations/{task_id}",
                    headers=self._get_headers(),
                    timeout=30,
                    verify=False  # 禁用 SSL 验证
                )
                break  # 成功则退出重试循环
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as ssl_err:
                if retry < max_retries - 1:
                    print(f"⚠️  SSL/连接错误 (重试 {retry+1}/{max_retries-1}): {ssl_err}")
                    time.sleep(2)  # 等待2秒后重试
                    continue
                else:
                    raise  # 最后一次重试失败则抛出异常
        
        try:
            response.raise_for_status()
            data = response.json()
            
            status = data.get("status", "unknown")
            # 视频URL在 data.output 字段
            video_url = (data.get("data", {}).get("output") or 
                        data.get("video_url") or 
                        data.get("url") or 
                        data.get("output_url"))
            
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
    
    def _check_kling_status(self, task_id: str) -> dict:
        """检查可灵任务状态"""
        try:
            response = requests.get(
                f"{self.base_url}/kling/v1/videos/text2video/{task_id}",
                headers=self._get_headers(),
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise VideoGenerationError(f"可灵状态查询错误: {data.get('message', '未知错误')}")
            
            task_data = data.get("data", {})
            status = task_data.get("task_status", "unknown")
            
            # 可灵视频URL在works数组中
            works = task_data.get("works", [])
            video_url = works[0].get("resource", {}).get("resource") if works else None
            
            return {
                "status": status,
                "video_url": video_url,
                "progress": task_data.get("progress"),
                "_raw_response": data,
                "_model_type": "kling"
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
        poll_interval: int = 60  # 每次间隔60秒
    ) -> dict:
        """
        轮询等待视频生成完成
        
        Args:
            task_id: 任务ID
            max_polls: 最大轮询次数(默认60次,总计10分钟)
            poll_interval: 轮询间隔(秒,默认10秒)
            
        Returns:
            {
                "status": "completed",
                "video_url": "视频URL"
            }
            
        Raises:
            VideoGenerationError: 生成失败或超时
        """
        model_type = "kling" if self._is_kling_model() else "sora"
        
        # 首次等待3分钟再开始轮询
        initial_wait = 180  # 3分钟
        print(f"⌛ [Transit2] 等待视频生成（初始延迟 {initial_wait//60} 分钟）...")
        print(f"   任务ID: {task_id}")
        print(f"   模型类型: {model_type}")
        time.sleep(initial_wait)
        
        print(f"⏳ [Transit2] 开始轮询任务状态")
        print(f"   轮询间隔: {poll_interval}秒")
        print(f"   最大轮询次数: {max_polls}")
        print(f"   预计最大等待时间: {initial_wait//60}分钟 + {max_polls * poll_interval//60}分钟")
        
        for attempt in range(max_polls):
            try:
                result = self.check_status(task_id, model_type)
                status = result.get("status", "").lower()
                
                print(f"  [{attempt+1}/{max_polls}] 状态: {status}", end="")
                if result.get("progress"):
                    print(f" ({result['progress']}%)", end="")
                print()
                
                # 完成状态（支持 SUCCESS 大写）
                if status.upper() in ["COMPLETED", "SUCCESS", "FINISHED", "SUCCEED"]:
                    video_url = result.get("video_url")
                    if not video_url:
                        raise VideoGenerationError("视频生成完成但未返回URL")
                    
                    print(f"✅ [Transit2] 视频生成完成")
                    print(f"   URL: {video_url[:80]}{'...' if len(video_url) > 80 else ''}")
                    
                    return {
                        "status": "completed",
                        "video_url": video_url,
                        "task_id": task_id
                    }
                
                # 失败状态
                elif status in ["failed", "error"]:
                    error_msg = result.get("error") or result.get("message") or "未知错误"
                    raise VideoGenerationError(f"视频生成失败: {error_msg}")
                
                # 处理中,继续等待
                elif status in ["not_start", "in_progress", "pending", "processing", "running", "queued", "submitted"]:
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
