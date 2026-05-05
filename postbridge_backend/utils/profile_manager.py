# -*- coding: utf-8 -*-
"""
用户配置目录管理器
管理每个账号的浏览器用户数据目录 (UserDataDir)
"""
import os
import sys
import shutil
import filelock
from pathlib import Path
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright, BrowserContext

# 平台名称映射
PLATFORM_NAMES = {
    1: 'xhs',       # 小红书
    2: 'shipinhao', # 视频号
    3: 'douyin',    # 抖音
    4: 'kuaishou',  # 快手
    5: 'bilibili',  # B站
}


def get_app_data_dir() -> Path:
    """获取应用数据目录（统一使用 conf.py 配置）"""
    from conf import get_app_data_dir as conf_get_app_data_dir
    app_data = conf_get_app_data_dir()
    profiles_dir = app_data / 'data' / 'profiles'
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


def get_profile_dir(platform_id: int, account_id: str) -> Path:
    """
    获取账号的用户配置目录
    
    Args:
        platform_id: 平台ID (1=小红书, 2=视频号, 3=抖音, 4=快手, 5=B站)
        account_id: 账号唯一标识
    
    Returns:
        Path: 用户配置目录路径
    """
    import sys
    platform_name = PLATFORM_NAMES.get(platform_id, f'platform_{platform_id}')
    app_data = get_app_data_dir()
    print(f"DEBUG [profile_manager]: app_data (from get_app_data_dir) = {app_data}", file=sys.__stdout__, flush=True)
    
    profile_dir = app_data / 'user_profiles' / f'{platform_name}_{account_id}'
    print(f"DEBUG [profile_manager]: profile_dir = {profile_dir}", file=sys.__stdout__, flush=True)
    
    # 确保目录存在
    profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"DEBUG [profile_manager]: mkdir called, exists now = {profile_dir.exists()}", file=sys.__stdout__, flush=True)
    
    return profile_dir


def get_profile_lock_path(profile_dir: Path) -> Path:
    """获取配置目录的锁文件路径"""
    return profile_dir.parent / f'.{profile_dir.name}.lock'


def is_profile_locked(profile_dir: Path) -> bool:
    """检查配置目录是否被其他进程占用（包括 Chrome 进程）"""
    # 方法1: 检查 filelock
    lock_path = get_profile_lock_path(profile_dir)
    if lock_path.exists():
        try:
            lock = filelock.FileLock(str(lock_path), timeout=0)
            lock.acquire()
            lock.release()
        except filelock.Timeout:
            return True
    
    # 方法2: 检查 Chrome 锁文件（Chrome 运行时会创建）
    chrome_lock_files = [
        profile_dir / 'SingletonLock',
        profile_dir / 'SingletonSocket',
        profile_dir / 'SingletonCookie',
    ]
    for lock_file in chrome_lock_files:
        if lock_file.exists():
            return True
    
    return False


def is_chrome_using_profile(profile_dir: Path) -> bool:
    """
    检查是否有 Chrome 进程正在使用此 UserDataDir
    通过检查 Chrome 的锁文件判断
    """
    # Chrome 运行时会在 user-data-dir 下创建这些锁文件
    lock_indicators = [
        profile_dir / 'SingletonLock',
        profile_dir / 'SingletonSocket', 
        profile_dir / 'SingletonCookie',
    ]
    
    for indicator in lock_indicators:
        if indicator.exists():
            return True
    
    return False


class ProfileLock:
    """配置目录锁（支持同步和异步上下文管理器）"""
    
    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self.lock_path = get_profile_lock_path(profile_dir)
        self.lock = filelock.FileLock(str(self.lock_path), timeout=10)
        self._acquired = False
    
    def __enter__(self):
        try:
            self.lock.acquire()
            self._acquired = True
            return self
        except filelock.Timeout:
            # 尝试清理残留锁后重试
            self._cleanup_stale_locks()
            try:
                self.lock.acquire(timeout=2)
                self._acquired = True
                return self
            except filelock.Timeout:
                raise RuntimeError(f"账号目录被占用: {self.profile_dir.name}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.force_release()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.force_release()
    
    def force_release(self):
        """强制释放锁（包括清理Chrome锁文件）"""
        # 释放 filelock
        if self._acquired:
            try:
                self.lock.release()
            except Exception:
                pass
            self._acquired = False
        
        # 清理 Chrome 残留锁文件
        self._cleanup_chrome_locks()
    
    def _cleanup_chrome_locks(self):
        """清理 Chrome 创建的锁文件"""
        chrome_lock_files = [
            self.profile_dir / 'SingletonLock',
            self.profile_dir / 'SingletonSocket',
            self.profile_dir / 'SingletonCookie',
        ]
        for lock_file in chrome_lock_files:
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception:
                pass
    
    def _cleanup_stale_locks(self):
        """清理可能残留的锁（超时重试前调用）"""
        # 清理 Chrome 锁文件
        self._cleanup_chrome_locks()
        
        # 尝试删除并重建 filelock 文件
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception:
            pass
    
    @staticmethod
    def cleanup_profile(profile_dir: Path):
        """静态方法：清理指定目录的所有锁（用于外部强制清理）"""
        lock_path = get_profile_lock_path(profile_dir)
        try:
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass
        
        chrome_lock_files = [
            profile_dir / 'SingletonLock',
            profile_dir / 'SingletonSocket',
            profile_dir / 'SingletonCookie',
        ]
        for lock_file in chrome_lock_files:
            try:
                if lock_file.exists():
                    lock_file.unlink()
            except Exception:
                pass


def get_optimized_chrome_args() -> list:
    """获取优化的 Chrome 启动参数（保留反检测，精简功能限制）"""
    return [
        # 反自动化检测（核心参数）
        '--disable-blink-features=AutomationControlled',
        '--disable-automation',
        
        # 基本运行参数
        '--no-sandbox',
        '--disable-dev-shm-usage',
        
        # 减少被检测风险
        '--disable-sync',
        '--disable-background-networking',
        
        # UI简化
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-infobars',
        '--disable-notifications',
        
        # 语言和窗口
        '--lang=zh-CN',
        '--window-size=1280,800',
    ]


async def launch_persistent_browser(
    profile_dir: Path,
    headless: bool = False,
    chrome_path: Optional[str] = None
) -> BrowserContext:
    """
    启动带 UserDataDir 的持久化浏览器上下文
    
    Args:
        profile_dir: 用户配置目录
        headless: 是否无头模式
        chrome_path: 自定义 Chrome 路径
    
    Returns:
        BrowserContext: 浏览器上下文
    """
    playwright = await async_playwright().start()
    
    launch_options = {
        'headless': headless,
        'args': get_optimized_chrome_args(),
        'ignore_default_args': ['--enable-automation'],
        'viewport': {'width': 1280, 'height': 800},
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    if chrome_path:
        launch_options['executable_path'] = chrome_path
    
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        **launch_options
    )
    
    # 保存 playwright 实例以便后续关闭
    context._playwright = playwright
    
    return context


async def close_persistent_browser(context: BrowserContext):
    """关闭持久化浏览器并清理资源"""
    playwright = getattr(context, '_playwright', None)
    await context.close()
    if playwright:
        await playwright.stop()
