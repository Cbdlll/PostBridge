# -*- coding: utf-8 -*-
"""
日志配置模块 - 带 rotation 防止磁盘爆满
"""
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

# 保存原始的 stdout/stderr 引用（在任何重定向之前）
_original_stdout = sys.stdout
_original_stderr = sys.stderr


def setup_logging(log_dir=None):
    """配置日志系统，自动rotation"""
    from conf import RUNTIME_DIR
    if log_dir is None:
        log_dir = RUNTIME_DIR / "logs"
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 打印日志目录位置（使用原始 stdout）
    print(f"📁 日志目录: {log_path}", file=_original_stdout, flush=True)
    
    # 文件handler，50MB rotation，保留5份
    handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=50 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    handlers = [handler]
    
    # 控制台handler - 始终使用原始 stderr 确保输出到真实终端
    console_handler = logging.StreamHandler(_original_stderr)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    handlers.append(console_handler)
    
    # 配置root logger
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
    
    # 开发环境下不再重定向 print，保持终端输出清晰
    # 如果需要将 print 也记录到日志，可以手动使用 logger
    
    logging.info("日志系统初始化完成 (rotation: 50MB, 保留5份)")
