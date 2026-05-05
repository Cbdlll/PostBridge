# -*- mode: python ; coding: utf-8 -*-
"""
Social Auto Upload - PyInstaller 打包配置
运行命令: pyinstaller app.spec
"""

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],  # 添加当前目录到搜索路径
    binaries=[],
    datas=[
        ('static', 'static'),           # 前端静态文件
        ('database/createTable.py', 'database'),  # 只打包建表脚本，不打包数据库
        ('ai_service', 'ai_service'),   # AI 服务模块
        ('rpa_service', 'rpa_service'), # RPA 模块
        ('utils', 'utils'),             # 工具模块
        ('logging_config.py', '.'),     # 日志配置模块
        ('conf.py', '.'),               # 配置模块
        ('scheduler.py', '.'),          # 调度器模块
        ('continue_task_api.py', '.'),  # 继续任务 API 模块
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'apscheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.interval',
        'cryptography',
        'filelock',
        'loguru',
        'logging_config',
        'conf',
        'scheduler',
        'continue_task_api',
        'requests',
        'urllib3',
        'sqlite3',
        'customtkinter',
        'waitress',
        'paste',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'PIL', 'cv2'],  # 保留 tkinter 用于弹窗
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PostBridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示命令行窗口，使用 GUI 模式
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='static/favicon.ico',  # 可选：添加应用图标
)
