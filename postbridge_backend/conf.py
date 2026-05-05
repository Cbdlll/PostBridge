# -*- coding: utf-8 -*-
"""
配置模块 - 支持 PyInstaller 打包和 Windows 运行
"""
import sys
import os
import json
from pathlib import Path

# 应用名称（用于数据目录）
APP_NAME = "PostBridge"


def get_base_dir():
    """获取应用基础目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，_MEIPASS 是临时解压目录
        return Path(sys._MEIPASS)
    return Path(__file__).parent.resolve()


def get_app_data_dir():
    """获取应用数据目录（统一存储 logs、data、profiles 等）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：使用系统 AppData 目录
        if sys.platform == 'win32':
            # Windows: C:\Users\{用户}\AppData\Local\AIOperationSystem
            base = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
            return base / APP_NAME
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Application Support/AIOperationSystem
            return Path.home() / 'Library' / 'Application Support' / APP_NAME
        else:
            # Linux: ~/.local/share/AIOperationSystem
            return Path.home() / '.local' / 'share' / APP_NAME
    else:
        # 开发环境：使用项目目录
        return Path(__file__).parent.resolve()


def get_runtime_dir():
    """获取运行时数据目录（用于 logs、data 等可写文件）"""
    return get_app_data_dir()


def get_chrome_path():
    """获取 Chrome 浏览器路径（支持自定义配置）"""
    # 1. 优先读取用户配置
    config_file = get_app_data_dir() / "data" / "app_config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                custom_path = config.get('chrome_path', '')
                if custom_path and Path(custom_path).exists():
                    return custom_path
        except Exception:
            pass
    
    # 2. Windows 默认路径检测
    if sys.platform == 'win32':
        default_paths = [
            Path(os.environ.get('PROGRAMFILES', r'C:\Program Files')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
        ]
        for path in default_paths:
            if path.exists():
                return str(path)
        return 'chrome.exe'  # 回退到 PATH 环境变量
    
    # 3. Linux 默认路径
    return '/usr/bin/google-chrome'


# 核心路径配置
BASE_DIR = get_base_dir()
RUNTIME_DIR = get_runtime_dir()

# 数据库路径（存储在运行时目录）
DATABASE_PATH = RUNTIME_DIR / "database" / "database.db"


def init_database():
    """初始化数据库（如果不存在则创建表结构）"""
    import sqlite3
    
    # 确保数据库目录存在
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果数据库已存在，跳过初始化
    if DATABASE_PATH.exists():
        return
    
    # 创建数据库和表
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 创建账号记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type INTEGER NOT NULL,
        filePath TEXT NOT NULL,
        userName TEXT NOT NULL,
        status INTEGER DEFAULT 0,
        last_validated_at DATETIME
    )
    ''')
    
    # 创建文件记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filesize REAL,
        upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        file_path TEXT
    )
    ''')
    
    # 创建 AI 创作任务表
    cursor.execute('''CREATE TABLE IF NOT EXISTS creation_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        prompt TEXT,
        title TEXT,
        description TEXT,
        tags TEXT,
        video_task_id TEXT,
        video_url TEXT,
        local_video_path TEXT,
        status TEXT DEFAULT 'pending',
        provider TEXT DEFAULT 'mock',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建发布任务表
    cursor.execute('''CREATE TABLE IF NOT EXISTS publish_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type TEXT NOT NULL,
        platform INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        tags TEXT,
        video_path TEXT,
        account_ids TEXT,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        progress INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {DATABASE_PATH}")


# 服务配置
XHS_SERVER = "http://127.0.0.1:11901"

# Chrome 配置
LOCAL_CHROME_PATH = get_chrome_path()
LOCAL_CHROME_HEADLESS = False  # 启用无头模式，避免弹出浏览器窗口
