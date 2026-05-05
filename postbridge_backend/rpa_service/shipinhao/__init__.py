# -*- coding: utf-8 -*-
"""
视频号 RPA 模块
使用 UserDataDir 持久化浏览器
"""
from pathlib import Path
from conf import RUNTIME_DIR

# 确保失败截图目录存在
(RUNTIME_DIR / "data" / "rpa_failed_screenshots" / "shipinhao").mkdir(parents=True, exist_ok=True)