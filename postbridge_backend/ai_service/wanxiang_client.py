# -*- coding: utf-8 -*-
"""
通义万相 (Wanxiang) 文生视频客户端
调用阿里云百炼平台 DashScope API
API文档: https://help.aliyun.com/zh/model-studio/developer-reference/text-to-video
"""
import os
import time
import requests
from typing import Optional
from pathlib import Path

try:
    from .video_client import VideoClient, VideoGenerationError
except ImportError:
    from video_client import VideoClient, VideoGenerationError


class WanxiangClient(VideoClient):
    """
    通义万相文生视频客户端
    
    支持模型:
    - wan2.6-t2v: 万相2.6 (推荐，支持有声视频和多镜头叙事)
    - wan2.5-t2v-preview: 万相2.5 preview
    - wan2.2-t2v-plus: 万相2.2专业版
    """
    
    # DashScope API 端点
    DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_INTL_URL = "https://dashscope-intl.aliyuncs.com/api/v1"
    
    # 视频生成端点
    VIDEO_SYNTHESIS_ENDPOINT = "/services/aigc/video-generation/video-synthesis"
    TASK_STATUS_ENDPOINT = "/tasks"
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "wan2.6-t2v",
        resolution: str = "720p",
        duration: int = 5,
        shot_type: str = "single",  # single=单镜头, multi=多镜头 (仅 wan2.6-t2v)
        watermark: bool = False,     # 是否添加水印
        prompt_extend: bool = False, # 禁用智能改写
        region: str = "cn",          # cn = 北京, intl = 新加坡
        output_dir: str = None,
        **kwargs
    ):
        """
        初始化通义万相客户端
        
        Args:
            api_key: DashScope API Key (环境变量: DASHSCOPE_API_KEY)
            model: 模型名称 (wan2.6-t2v, wan2.5-t2v-preview, wan2.2-t2v-plus)
            resolution: 分辨率 (720p, 1080p)
            duration: 视频时长 (5, 10, 15 秒，取决于模型)
            shot_type: 镜头类型 (single=单镜头, multi=多镜头，仅 wan2.6-t2v 支持)
            watermark: 是否添加水印
            prompt_extend: 是否开启prompt智能改写
            region: 地域 (cn=北京, intl=新加坡)
            output_dir: 输出目录
        """
        super().__init__(api_key=api_key, output_dir=output_dir, **kwargs)
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model
        self.resolution = resolution
        self.duration = duration
        self.shot_type = shot_type
        self.watermark = watermark
        self.prompt_extend = prompt_extend
        
        # 根据地域选择 API 端点
        if region == "intl":
            self.base_url = self.DASHSCOPE_INTL_URL
        else:
            self.base_url = self.DASHSCOPE_BASE_URL
    
    def _get_headers(self) -> dict:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"  # 启用异步模式
        }
    
    def _map_resolution(self) -> str:
        """
        映射分辨率参数为具体尺寸
        API 要求 size 为具体数值（如 1280*720），而非 720P
        """
        resolution_map = {
            "720p": "1280*720",
            "1080p": "1920*1080"
        }
        return resolution_map.get(self.resolution.lower(), "1280*720")
    
    def generate_video(self, prompt: str, **kwargs) -> dict:
        """
        调用通义万相 API 创建视频生成任务
        
        Args:
            prompt: 视频提示词 (支持中英文)
            **kwargs: 额外参数
                - negative_prompt: 反向提示词
                - seed: 随机种子
        
        Returns:
            {
                "task_id": "任务ID",
                "status": "pending/processing/completed/failed",
                "video_url": None,
                "local_path": None
            }
        """
        if not self.api_key:
            raise VideoGenerationError("未配置 DASHSCOPE_API_KEY")
        
        # 构建请求体
        shot_type = kwargs.get("shot_type", self.shot_type)
        watermark = kwargs.get("watermark", self.watermark)
        prompt_extend = kwargs.get("prompt_extend", self.prompt_extend)
        
        payload = {
            "model": kwargs.get("model", self.model),
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": self._map_resolution(),
                "duration": kwargs.get("duration", self.duration),
                "prompt_extend": prompt_extend,
                "watermark": watermark
            }
        }
        
        # shot_type 仅 wan2.6-t2v 支持
        if self.model == "wan2.6-t2v":
            payload["parameters"]["shot_type"] = shot_type
        
        # 可选：反向提示词
        if kwargs.get("negative_prompt"):
            payload["input"]["negative_prompt"] = kwargs["negative_prompt"]
        
        # 可选：随机种子
        if kwargs.get("seed"):
            payload["parameters"]["seed"] = kwargs["seed"]
        
        url = f"{self.base_url}{self.VIDEO_SYNTHESIS_ENDPOINT}"
        
        try:
            print(f"🎬 [Wanxiang] 创建视频生成任务...")
            print(f"   模型: {payload['model']}")
            print(f"   分辨率: {payload['parameters']['size']}")
            print(f"   时长: {payload['parameters']['duration']}秒")
            print(f"   镜头类型: {payload['parameters'].get('shot_type', 'N/A')}")
            print(f"   水印: {payload['parameters']['watermark']}")
            print(f"   智能改写: {payload['parameters']['prompt_extend']}")
            print(f"   Prompt: {prompt[:80]}...")
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            
            # 处理响应
            data = response.json()
            
            # 检查错误
            if "code" in data and data["code"] != "":
                error_msg = data.get("message", "未知错误")
                raise VideoGenerationError(f"通义万相 API 错误: {data.get('code')} - {error_msg}")
            
            # 获取任务ID
            output = data.get("output", {})
            task_id = output.get("task_id")
            task_status = output.get("task_status", "PENDING")
            
            if not task_id:
                raise VideoGenerationError(f"未获取到任务ID: {data}")
            
            print(f"   ✅ 任务已创建: {task_id}")
            
            return {
                "task_id": task_id,
                "status": self._map_status(task_status),
                "video_url": None,
                "local_path": None,
                "provider": "wanxiang",
                "_raw_status": task_status
            }
            
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"通义万相 API 请求失败: {e}") from e
    
    def check_status(self, task_id: str) -> dict:
        """
        查询视频生成任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            {
                "status": "pending/processing/completed/failed",
                "video_url": "视频URL (完成后)",
                "progress": 进度百分比
            }
        """
        if not self.api_key:
            raise VideoGenerationError("未配置 DASHSCOPE_API_KEY")
        
        url = f"{self.base_url}{self.TASK_STATUS_ENDPOINT}/{task_id}"
        
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            
            data = response.json()
            output = data.get("output", {})
            
            task_status = output.get("task_status", "UNKNOWN")
            video_url = output.get("video_url")
            
            # 计算进度
            progress = 0
            if task_status == "PENDING":
                progress = 10
            elif task_status == "RUNNING":
                progress = 50
            elif task_status == "SUCCEEDED":
                progress = 100
            elif task_status == "FAILED":
                progress = 0
            
            result = {
                "status": self._map_status(task_status),
                "video_url": video_url,
                "progress": progress,
                "_raw_status": task_status
            }
            
            # 如果失败，添加错误信息
            if task_status == "FAILED":
                result["error"] = output.get("message", "视频生成失败")
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise VideoGenerationError(f"状态查询失败: {e}") from e
    
    def _map_status(self, raw_status: str) -> str:
        """映射 DashScope 状态到统一状态"""
        status_map = {
            "PENDING": "pending",
            "RUNNING": "processing",
            "SUCCEEDED": "completed",
            "FAILED": "failed",
            "CANCELED": "failed",
            "UNKNOWN": "failed"
        }
        return status_map.get(raw_status, "pending")
    
    def wait_for_completion(self, task_id: str, poll_interval: int = 60, max_wait: int = 1800) -> dict:
        """
        等待视频生成完成
        
        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔 (秒)，默认 60 秒
            max_wait: 最大等待时间 (秒)，默认 1800 秒（30 分钟）
            
        Returns:
            最终状态
            
        Raises:
            VideoGenerationError: 生成失败或超时
        """
        start_time = time.time()
        poll_count = 0
        max_polls = max_wait // poll_interval
        
        # 首次等待3分钟再开始轮询
        initial_wait = 180  # 3分钟
        print(f"   ⌛ 等待视频生成（初始延迟 {initial_wait//60} 分钟）...")
        time.sleep(initial_wait)
        
        print(f"   ⏳ 开始轮询视频生成状态 (最多 {max_polls} 次，间隔 {poll_interval} 秒)")
        
        while time.time() - start_time < max_wait:
            poll_count += 1
            elapsed = int(time.time() - start_time)
            
            try:
                result = self.check_status(task_id)
                status = result.get("status")
                
                print(f"   [{poll_count}/{max_polls}] 状态: {result.get('_raw_status')} ({result.get('progress')}%) - 已等待 {elapsed}秒")
                
                if status == "completed":
                    print(f"   ✅ 视频生成完成! 总耗时 {elapsed} 秒")
                    return result
                elif status == "failed":
                    error_msg = result.get('error', '未知错误')
                    raise VideoGenerationError(f"视频生成失败: {error_msg}")
                
            except VideoGenerationError:
                raise
            except Exception as e:
                print(f"   ⚠️ 状态查询异常: {e}, 继续轮询...")
            
            time.sleep(poll_interval)
        
        # 超时处理
        elapsed = int(time.time() - start_time)
        error_msg = f"视频生成超时: 已等待 {elapsed} 秒（{elapsed // 60} 分钟），超过最大等待时间 {max_wait} 秒"
        print(f"   ❌ {error_msg}")
        raise VideoGenerationError(error_msg)

