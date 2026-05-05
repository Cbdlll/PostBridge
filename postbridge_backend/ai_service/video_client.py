# -*- coding: utf-8 -*-
"""
Video Client - 文生视频 API 调用客户端
支持多种视频生成服务（Runway, Pika, 可灵等）
"""
import os
import time
import requests
from typing import Optional
from pathlib import Path


class VideoGenerationError(Exception):
    """视频生成相关异常"""
    pass


class VideoClient:
    """
    视频生成客户端 - 抽象基类
    子类需要实现具体的 API 调用逻辑
    """
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        output_dir: str = None,
        timeout: int = 300
    ):
        """
        初始化视频客户端
        
        Args:
            api_key: API 密钥
            base_url: API 基础地址
            output_dir: 视频输出目录
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or os.getenv("VIDEO_API_KEY", "")
        self.base_url = (base_url or os.getenv("VIDEO_API_BASE_URL", "")).rstrip("/")
        self.output_dir = Path(output_dir) if output_dir else Path("data/videos")
        self.timeout = timeout
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_video(self, prompt: str, **kwargs) -> dict:
        """
        生成视频 - 需要子类实现
        
        Args:
            prompt: 视频生成提示词
            **kwargs: 其他参数
            
        Returns:
            {
                "task_id": "任务ID",
                "status": "pending/processing/completed/failed",
                "video_url": "视频URL（完成后）",
                "local_path": "本地路径（下载后）"
            }
        """
        raise NotImplementedError("子类必须实现 generate_video 方法")

    def check_status(self, task_id: str) -> dict:
        """
        检查视频生成状态 - 需要子类实现
        
        Returns:
            {"status": "...", "video_url": "..."}
        """
        raise NotImplementedError("子类必须实现 check_status 方法")

    def download_video(self, video_url: str, filename: str = None) -> str:
        """
        下载视频到本地
        
        Args:
            video_url: 视频 URL
            filename: 保存的文件名（可选）
            
        Returns:
            本地文件路径
        """
        if not filename:
            filename = f"gen_{int(time.time())}.mp4"
        
        local_path = self.output_dir / filename
        
        try:
            response = requests.get(video_url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ 视频已下载: {local_path}")
            return str(local_path)
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"视频下载失败: {e}") from e


class MockVideoClient(VideoClient):
    """
    模拟视频客户端 - 用于开发测试
    不实际调用 API，返回模拟数据，但执行完整的后续流程（下载、存储、发布）
    """
    
    def __init__(self, mock_video_url: str = None, **kwargs):
        """
        初始化 Mock 视频客户端
        
        Args:
            mock_video_url: 自定义的 Mock 视频 URL（必需）
            **kwargs: 其他参数传递给父类
        """
        super().__init__(**kwargs)
        self.mock_video_url = mock_video_url or ""
        
        if self.mock_video_url:
            print(f"🎭 [Mock] 使用配置的视频 URL: {self.mock_video_url[:80]}...")
        else:
            print(f"⚠️  [Mock] 未配置 Mock 视频 URL，请在系统设置中配置")
    
    def generate_video(self, prompt: str, **kwargs) -> dict:
        """模拟视频生成"""
        import uuid
        task_id = str(uuid.uuid4())
        
        print(f"🎬 [Mock] 模拟视频生成任务已创建")
        print(f"   Prompt: {prompt[:100]}...")
        print(f"   Task ID: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "video_url": None,
            "local_path": None,
            "_mock": True,
            "_prompt": prompt
        }
    
    def check_status(self, task_id: str) -> dict:
        """模拟状态检查 - 返回配置的示例视频URL"""
        if not self.mock_video_url:
            print(f"  [Mock] ⚠️  未配置 Mock 视频 URL")
            return {
                "status": "failed",
                "error": "未配置 Mock 视频 URL，请在系统设置中配置",
                "_mock": True
            }
        
        print(f"  [Mock] 返回配置的示例视频: {self.mock_video_url[:80]}...")
        
        return {
            "status": "completed",
            "video_url": self.mock_video_url,
            "_mock": True
        }
    
    def wait_for_completion(self, task_id: str, max_polls: int = 30, poll_interval: int = 60) -> dict:
        """
        模拟等待视频生成完成 - 直接返回配置的视频URL
        这样后续的下载、存储、自动发布都会正常执行
        """
        import time
        
        print(f"🎭 [Mock] 模拟视频生成等待...")
        
        if not self.mock_video_url:
            print(f"❌ [Mock] 未配置 Mock 视频 URL")
            return {
                "status": "failed",
                "error": "未配置 Mock 视频 URL，请在系统设置中配置",
                "_mock": True
            }
        
        time.sleep(1)  # 模拟短暂延迟
        
        print(f"✅ [Mock] 视频生成完成（使用配置的视频）")
        print(f"   视频URL: {self.mock_video_url[:80]}...")
        
        return {
            "status": "completed",
            "video_url": self.mock_video_url,
            "_mock": True
        }


class RunwayClient(VideoClient):
    """
    Runway Gen-3 Alpha API 客户端
    文档: https://docs.runway.ml/
    """
    
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        if not self.base_url:
            self.base_url = "https://api.runway.ml/v1"
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, duration: int = 4, **kwargs) -> dict:
        """
        调用 Runway API 生成视频
        
        Args:
            prompt: 视频提示词（英文）
            duration: 视频时长（秒）
        """
        payload = {
            "prompt": prompt,
            "duration": duration,
            # 根据 Runway API 文档添加其他参数
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generations",
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "task_id": data.get("id"),
                "status": data.get("status", "pending"),
                "video_url": data.get("output", {}).get("url"),
                "local_path": None
            }
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"Runway API 调用失败: {e}") from e
    
    def check_status(self, task_id: str) -> dict:
        """检查 Runway 任务状态"""
        try:
            response = requests.get(
                f"{self.base_url}/generations/{task_id}",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": data.get("status"),
                "video_url": data.get("output", {}).get("url")
            }
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"状态查询失败: {e}") from e


class KeLingClient(VideoClient):
    """
    可灵 (KeLing) API 客户端
    国产文生视频模型
    """
    
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        if not self.base_url:
            self.base_url = os.getenv("KELING_API_BASE_URL", "")
    
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_video(self, prompt: str, **kwargs) -> dict:
        """
        调用可灵 API 生成视频
        
        注意: 具体参数需要根据可灵官方 API 文档调整
        """
        payload = {
            "prompt": prompt,
            # 根据可灵 API 文档添加其他参数
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "task_id": data.get("task_id"),
                "status": "pending",
                "video_url": None,
                "local_path": None
            }
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"可灵 API 调用失败: {e}") from e
    
    def check_status(self, task_id: str) -> dict:
        """检查可灵任务状态"""
        try:
            response = requests.get(
                f"{self.base_url}/task/{task_id}",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": data.get("status"),
                "video_url": data.get("video_url")
            }
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"状态查询失败: {e}") from e


def get_video_client(provider: str = "mock", **kwargs) -> VideoClient:
    """
    工厂函数：根据 provider 返回对应的视频客户端
    
    Args:
        provider: 服务商名称 ("mock", "wanxiang", "sora", "doubao")
        **kwargs: 传递给客户端的参数
        
    Returns:
        VideoClient 实例
    """
    # 延迟导入以避免循环依赖
    from .wanxiang_client import WanxiangClient
    from .transit2_client import Transit2Client
    from .doubao_client import DoubaoClient
    
    clients = {
        "mock": MockVideoClient,
        "wanxiang": WanxiangClient,
        "sora": Transit2Client,  # 中转站（原中转站2）
        "doubao": DoubaoClient,  # 豆包SeeDance
    }
    
    client_class = clients.get(provider.lower())
    if not client_class:
        raise ValueError(f"不支持的视频服务商: {provider}. 可用: {list(clients.keys())}")
    
    # 根据不同的 client 过滤参数，避免传递不相关的 kwargs
    # 各客户端接受的参数白名单
    common_params = {'api_key', 'base_url', 'output_dir', 'timeout'}
    mock_params = common_params | {'mock_video_url'}
    wanxiang_params = common_params | {'resolution', 'duration', 'shot_type', 'watermark', 'model'}
    sora_params = common_params | {'resolution', 'duration', 'model'}
    transit2_params = common_params | {'model', 'duration'}
    doubao_params = common_params | {'model'}
    
    param_whitelist = {
        "mock": mock_params,
        "wanxiang": wanxiang_params,
        "sora": transit2_params,  # 使用 Transit2Client 的参数配置
        "doubao": doubao_params,
    }
    
    allowed_params = param_whitelist.get(provider.lower(), common_params)
    # 过滤参数：1. key在白名单中，2. value不为None（避免覆盖默认值）
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params and v is not None}
    
    return client_class(**filtered_kwargs)

