# -*- coding: utf-8 -*-
"""
视频封面提取工具 - 从视频开头自动提取封面帧
使用FFmpeg从视频提取关键帧作为封面
"""
import subprocess
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_thumbnail_from_video(
    video_path: str,
    output_path: Optional[str] = None,
    timestamp: str = "00:00:01",
    quality: int = 2
) -> Optional[str]:
    """
    使用FFmpeg从视频中提取封面帧
    
    Args:
        video_path: 视频文件路径
        output_path: 输出图片路径，默认为视频同目录下的 {video_name}_cover.jpg
        timestamp: 提取帧的时间点，默认第1秒
        quality: 图片质量 (1-31, 越小越好)
    
    Returns:
        生成的封面图片路径，失败返回 None
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return None
    
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_cover.jpg"
    else:
        output_path = Path(output_path)
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # FFmpeg命令：提取指定时间点的帧
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖已存在文件
            "-ss", str(timestamp),  # 时间点
            "-i", str(video_path),  # 输入视频
            "-vframes", "1",  # 只提取1帧
            "-q:v", str(quality),  # 图片质量
            "-vf", "scale='min(1920,iw)':-1",  # 限制最大宽度为1920，保持比例
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and output_path.exists():
            logger.info(f"封面提取成功: {output_path}")
            return str(output_path)
        else:
            logger.error(f"FFmpeg执行失败: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg执行超时")
        return None
    except FileNotFoundError:
        logger.error("未找到FFmpeg，请确保已安装并添加到PATH")
        return None
    except Exception as e:
        logger.error(f"提取封面时出错: {e}")
        return None


def get_video_duration(video_path: str) -> Optional[float]:
    """
    获取视频时长（秒）
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        视频时长（秒），失败返回None
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"获取视频时长失败: {e}")
    return None


def extract_thumbnail_from_start(
    video_path: str,
    output_dir: Optional[str] = None
) -> Optional[str]:
    """
    从视频开头提取封面（默认第1秒）
    这是AI视频发布的推荐方法
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录，默认为视频所在目录
    
    Returns:
        封面图片路径，失败返回None
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return None
    
    if output_dir is None:
        output_dir = video_path.parent
    
    output_path = Path(output_dir) / f"{video_path.stem}_cover.jpg"
    
    # 从视频开头第1秒提取
    return extract_thumbnail_from_video(
        str(video_path),
        str(output_path),
        timestamp="1"
    )


def check_ffmpeg_available() -> bool:
    """检查FFmpeg是否可用"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


# 保持向后兼容的别名
extract_best_thumbnail = extract_thumbnail_from_start

