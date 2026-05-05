import asyncio
import atexit
import os
import sqlite3

# 初始化日志系统 (带rotation防止磁盘爆满)
from logging_config import setup_logging
setup_logging()
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from queue import Queue
from flask_cors import CORS
from rpa_service.auth import check_cookie
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from conf import BASE_DIR, RUNTIME_DIR, LOCAL_CHROME_PATH, DATABASE_PATH, init_database

# 初始化数据库（如果不存在）
init_database()
from rpa_service.coordinator import post_video_tencent, post_video_DouYin, post_video_ks, post_video_xhs, post_video_DouYin_with_taskid, post_video_bilibili
from utils.global_state import active_queues, verification_queues
from utils.profile_manager import get_profile_dir, is_chrome_using_profile
import json
import sys

# === 启动诊断日志 ===
print("="*50, file=sys.__stdout__)
print(f"DEBUG: sys.frozen = {getattr(sys, 'frozen', 'NOT SET')}", file=sys.__stdout__)
print(f"DEBUG: sys.executable = {sys.executable}", file=sys.__stdout__)
print(f"DEBUG: BASE_DIR = {BASE_DIR}", file=sys.__stdout__)
print(f"DEBUG: RUNTIME_DIR (Data Dir) = {RUNTIME_DIR}", file=sys.__stdout__)
print("="*50, file=sys.__stdout__, flush=True)

from ai_service.llm_client import LLMClient, generate_video_prompt
from ai_service.video_client import get_video_client, VideoGenerationError
from ai_service.platform_personas import PLATFORM_PERSONAS, PLATFORM_PERSONAS_EN
from scheduler import init_scheduler, shutdown_scheduler, is_cache_valid, get_last_validated_time, VALIDATION_INTERVAL_SECONDS

# 导入 Blueprint 模块
from continue_task_api import continue_task_bp

def normalize_persona_lang(value):
    return "en" if value == "en" else "zh-CN"

# Helper to parse markdown prompt into UI data
def parse_persona_prompt(prompt_text):
    import re
    data = {"features": {}, "hot_topics": "", "description": ""}

    def extract_section(start_labels, end_labels=None):
        start = "|".join(re.escape(label) for label in start_labels)
        pattern = rf'\*\*(?:{start})[：:]\*\*\s*(.*?)'
        if end_labels:
            end = "|".join(re.escape(label) for label in end_labels)
            pattern += rf'\s*(?=\*\*(?:{end})[：:]\*\*)'
        else:
            pattern += r'\s*$'
        match = re.search(pattern, prompt_text, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    # Extract Name (Assumes format: ### Name (Code) ...)
    # But usually we have code from the key. We just need to parse the content sections.
    
    users = extract_section(
        ["用户群体", "Audience Segments"],
        ["内容风格要求", "Content Style Requirements"],
    )
    if users:
        data["features"]["users"] = users
        
    style = extract_section(
        ["内容风格要求", "Content Style Requirements"],
        ["近期热点/流行趋势 (Trends)", "Recent Hot Topics / Trends", "内容关键词", "Content Keywords"],
    )
    if style:
        data["features"]["style"] = style
        
    keywords = extract_section(["内容关键词", "Content Keywords"])
    if keywords:
        raw_kw = keywords
        # Fix: Remove trailing period if present
        if raw_kw.endswith('.') or raw_kw.endswith('。'):
            raw_kw = raw_kw[:-1]
            
        # Split by various separators
        kws = [k.strip() for k in re.split(r'[、,，;；\n]+', raw_kw) if k.strip()]
        data["features"]["keywords"] = kws
        
    # 4. Description (We can just use a generic summary or try to extract from Users first line?)
    # For now, let's just use the first bullet of Users as description or leave empty/generic.
    # Actually, we can just leave it editable. Or try to grab the first text block.
    if data["features"]["users"]:
        lines = data["features"]["users"].split('\n')
        for line in lines:
            if "总体规模" in line or "用户规模" in line or "Overall Reach" in line:
                 data["description"] = line.replace("*", "").strip()
                 break
        if not data["description"] and lines:
             data["description"] = lines[0].replace("*", "").strip()

    return data

def init_persona_db():
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Explicitly drop table to reset as requested
            cursor.execute("DROP TABLE IF EXISTS platform_personas")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS platform_personas (
                    language TEXT NOT NULL DEFAULT 'zh-CN',
                    platform_code TEXT NOT NULL,
                    platform_name TEXT,
                    persona_prompt TEXT,
                    ui_data TEXT,
                    PRIMARY KEY (language, platform_code)
                )
            ''')
            
            # Check count (should be 0 after drop)
            cursor.execute("SELECT count(*) FROM platform_personas")
            if cursor.fetchone()[0] == 0:
                print("🚀 Initializing platform personas database from file...")
                
                platform_names = {
                    "zh-CN": {
                        "douyin": "抖音",
                        "ks": "快手",
                        "xhs": "小红书",
                        "wx": "视频号",
                        "bilibili": "B站"
                    },
                    "en": {
                        "douyin": "Douyin",
                        "ks": "Kuaishou",
                        "xhs": "Xiaohongshu",
                        "wx": "WeChat Channels",
                        "bilibili": "Bilibili"
                    }
                }

                platform_colors = {
                    "douyin": "#000000",
                    "xhs": "#eb1e32",
                    "ks": "#ff4906",
                    "wx": "#07c160",
                    "bilibili": "#00a1d6"
                }
                
                platform_icons = {
                    "douyin": "video-play",
                    "xhs": "camera",
                    "ks": "video-camera",
                    "wx": "chat-dot-round",
                    "bilibili": "video-camera"
                }

                persona_sources = {
                    "zh-CN": PLATFORM_PERSONAS,
                    "en": PLATFORM_PERSONAS_EN
                }

                for lang, personas in persona_sources.items():
                    for code, prompt in personas.items():
                        # Parse Prompt
                        ui_data = parse_persona_prompt(prompt)
                        
                        # Add static UI fields
                        name = platform_names[lang].get(code, code)
                        ui_data["name"] = name
                        ui_data["color"] = platform_colors.get(code, "#333")
                        ui_data["icon"] = platform_icons.get(code, "video-play")
                        
                        ui_json = json.dumps(ui_data, ensure_ascii=False)
                        
                        cursor.execute(
                            "INSERT INTO platform_personas (language, platform_code, platform_name, persona_prompt, ui_data) VALUES (?, ?, ?, ?, ?)",
                            (lang, code, name, prompt, ui_json)
                        )
                conn.commit()
                print("✅ Platform personas initialized.")

    except Exception as e:
        print(f"❌ DB Init Error: {e}")

# Call init immediately
init_persona_db()


# ============== 启动时清理残留锁文件 ==============
def cleanup_stale_locks():
    """
    启动时清理残留的 .lock 文件和 Chrome Singleton 文件
    这些文件可能因为上次异常退出而残留
    """
    try:
        profiles_dir = Path(BASE_DIR / "data" / "profiles" / "user_profiles")
        if not profiles_dir.exists():
            return
        
        # 清理 .lock 文件
        lock_files = list(profiles_dir.glob(".*lock"))
        for lock_file in lock_files:
            try:
                lock_file.unlink()
                print(f"🧹 已清理残留锁文件: {lock_file.name}")
            except Exception as e:
                print(f"⚠️ 清理锁文件失败: {lock_file.name} - {e}")
        
        # 清理每个 profile 目录中的 Chrome Singleton 文件
        for profile_dir in profiles_dir.iterdir():
            if profile_dir.is_dir():
                singleton_files = ['SingletonLock', 'SingletonSocket', 'SingletonCookie']
                for sf in singleton_files:
                    sf_path = profile_dir / sf
                    if sf_path.exists():
                        try:
                            sf_path.unlink()
                            print(f"🧹 已清理 Chrome 锁文件: {profile_dir.name}/{sf}")
                        except Exception:
                            pass
        
        if lock_files:
            print(f"✅ 启动清理完成: 共清理 {len(lock_files)} 个残留锁文件")
        
    except Exception as e:
        print(f"⚠️ 启动清理过程出错: {e}")

# 启动时执行清理
cleanup_stale_locks()



# ============== SQLite WAL 优化 ==============
def get_optimized_connection():
    """
    获取优化后的SQLite连接
    - WAL模式: 写入不阻塞读取
    - NORMAL同步: 性能与安全平衡
    - 增大缓存: 减少磁盘IO
    """
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30.0
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=5000")
    return conn

def verify_login_by_cookies_db(profile_dir: Path, platform: str) -> bool:
    """
    通过查询 Cookies SQLite 数据库验证登录状态
    比单纯检查文件大小更准确
    """
    cookies_db = profile_dir / 'Default' / 'Cookies'
    if not cookies_db.exists():
        print(f"❌ Cookies 文件不存在: {cookies_db}")
        return False
        
    # 如果文件小于 4KB，肯定是空的
    if cookies_db.stat().st_size < 4096:
        print(f"⚠️ Cookies 文件过小 ({cookies_db.stat().st_size} bytes)，认为未登录")
        return False
    
    domain_keywords = {
        'douyin': ['douyin.com'],
        'xhs': ['xiaohongshu.com'],
        'kuaishou': ['kuaishou.com', 'kuaishouzt.com'],
        'bilibili': ['bilibili.com'],
        'shipinhao': ['qq.com', 'weixin.qq.com'] 
    }
    
    keywords = domain_keywords.get(platform, [])
    if not keywords:
        # 未知平台，回退到文件大小 > 10KB
        size_kb = cookies_db.stat().st_size / 1024
        print(f"ℹ️ 未知平台 {platform}，使用文件大小判断: {size_kb:.1f}KB")
        return size_kb > 10
        
    try:
        # 连接 Cookies 数据库 (只读模式)
        uri = f"file:{cookies_db}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        cursor = conn.cursor()
        
        total_cookies = 0
        for keyword in keywords:
            # host_key 存储域名，如 .douyin.com
            query = "SELECT count(*) FROM cookies WHERE host_key LIKE ?"
            cursor.execute(query, (f'%{keyword}%',))
            count = cursor.fetchone()[0]
            total_cookies += count
            
        conn.close()
        
        print(f"🍪 [{platform}] 检测到相关域名Cookies数量: {total_cookies}")
        
        # 只要有相关域名的 cookies，就认为登录过
        # 登录成功通常会有多个关键 Cookie
        return total_cookies > 0
        
    except Exception as e:
        print(f"⚠️ 读取 Cookies 数据库失败: {e}")
        # 降级策略：如果读库失败，使用宽松的文件大小检查 (15KB)
        # 用户反馈登录后可能只有 20KB-32KB
        size_kb = cookies_db.stat().st_size / 1024
        print(f"⚠️ 降级策略：检查文件大小 > 15KB (当前: {size_kb:.1f}KB)")
        return size_kb > 15



app = Flask(__name__)

#允许所有来源跨域访问
CORS(app)

# 全局请求日志 (调试用)
@app.before_request
def log_request_info():
    import sys
    print(f"DEBUG: Incoming Request: {request.method} {request.url}", file=sys.__stdout__, flush=True)

# 限制上传文件大小为160MB
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024

# 注册 Blueprint
app.register_blueprint(continue_task_bp)

# 获取静态文件目录（兼容 PyInstaller 打包）
import sys
def get_static_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'static')
    return os.path.dirname(os.path.abspath(__file__))

current_dir = get_static_dir()

# 处理所有静态资源请求（未来打包用）
@app.route('/assets/<filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(current_dir, 'assets'), filename)

# 处理 favicon.ico 静态资源（未来打包用）
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

@app.route('/vite.svg')
def vite_svg():
    return send_from_directory(os.path.join(current_dir, 'assets'), 'vite.svg')

# （未来打包用）
@app.route('/')
def index():  # put application's code here
    return send_from_directory(current_dir, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No file part in the request"
        }), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 200,
            "data": None,
            "msg": "No selected file"
        }), 400
    try:
        # 保存文件到指定位置
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        filepath = Path(RUNTIME_DIR / "data/videos" / f"{uuid_v1}_{file.filename}")
        
        # 确保目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        file.save(filepath)
        return jsonify({"code":200,"msg": "File uploaded successfully", "data": f"{uuid_v1}_{file.filename}"}), 200
    except Exception as e:
        return jsonify({"code":200,"msg": str(e),"data":None}), 500

@app.route('/getFile', methods=['GET'])
def get_file():
    # 获取 filename 参数
    filename = request.args.get('filename')

    if not filename:
        return {"error": "filename is required"}, 400

    # 如果是绝对路径，提取文件名
    if filename.startswith('/'):
        filename = os.path.basename(filename)
    
    # 防止路径穿越攻击（仅检查 ..）
    if '..' in filename:
        return {"error": "Invalid filename"}, 400

    # 拼接完整路径
    file_path = str(Path(RUNTIME_DIR / "data/videos"))

    # 返回文件
    return send_from_directory(file_path, filename)


# ============== Chrome 配置 API ==============
@app.route('/api/config', methods=['GET'])
def get_app_config():
    """获取应用配置"""
    config_file = RUNTIME_DIR / "data" / "app_config.json"
    config = {"chrome_path": LOCAL_CHROME_PATH}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    return jsonify({"code": 200, "data": config})

@app.route('/api/config', methods=['POST'])
def save_app_config():
    """保存应用配置"""
    data = request.get_json() or {}
    config_file = RUNTIME_DIR / "data" / "app_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 验证 Chrome 路径
    chrome_path = data.get('chrome_path', '')
    if chrome_path and not Path(chrome_path).exists():
        return jsonify({"code": 400, "msg": f"Chrome 路径不存在: {chrome_path}"})
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 热更新 conf 模块
    import conf
    conf.LOCAL_CHROME_PATH = chrome_path if chrome_path else conf.get_chrome_path()
    
    return jsonify({"code": 200, "msg": "配置已保存"})


@app.route('/api/check-llm', methods=['POST'])
def check_llm():
    data = request.get_json()
    base_url = data.get('baseUrl')
    api_key = data.get('apiKey')
    model = data.get('model')

    if not all([base_url, api_key, model]):
        return jsonify({"code": 400, "msg": "Missing parameters"}), 400

    try:
        client = LLMClient(base_url=base_url, api_key=api_key, model=model, timeout=10)
        # Try a simple prompt to verify connection
        response = client.chat(user_message="Hello", max_tokens=5)
        return jsonify({"code": 200, "msg": "Connection successful", "data": response}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": f"Connection failed: {str(e)}"}), 500

@app.route('/uploadSave', methods=['POST'])
def upload_save():
    if 'file' not in request.files:
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No file part in the request"
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "code": 400,
            "data": None,
            "msg": "No selected file"
        }), 400

    # 获取表单中的自定义文件名（可选）
    custom_filename = request.form.get('filename', None)
    if custom_filename:
        filename = custom_filename + "." + file.filename.split('.')[-1]
    else:
        filename = file.filename

    try:
        # 生成 UUID v1
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")

        # 构造文件名和路径
        final_filename = f"{uuid_v1}_{filename}"
        filepath = Path(RUNTIME_DIR / "data/videos" / f"{uuid_v1}_{filename}")

        # 确保目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file.save(filepath)

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                                INSERT INTO file_records (filename, filesize, file_path)
            VALUES (?, ?, ?)
                                ''', (filename, round(float(os.path.getsize(filepath)) / (1024 * 1024),2), final_filename))
            conn.commit()
            print("✅ 上传文件已记录")

        return jsonify({
            "code": 200,
            "msg": "File uploaded and saved successfully",
            "data": {
                "filename": filename,
                "filepath": final_filename
            }
        }), 200

    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({
            "code": 500,
            "msg": f"upload failed: {e}",
            "data": None
        }), 500

@app.route('/getFiles', methods=['GET'])
def get_all_files():
    try:
        # 使用 with 自动管理数据库连接
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
            cursor = conn.cursor()

            # 查询所有记录
            cursor.execute("SELECT * FROM file_records")
            rows = cursor.fetchall()

            # 将结果转为字典列表，并提取UUID
            data = []
            for row in rows:
                row_dict = dict(row)
                # 从 file_path 中提取 UUID (文件名的第一部分，下划线前)
                if row_dict.get('file_path'):
                    file_path_parts = row_dict['file_path'].split('_', 1)  # 只分割第一个下划线
                    if len(file_path_parts) > 0:
                        row_dict['uuid'] = file_path_parts[0]  # UUID 部分
                    else:
                        row_dict['uuid'] = ''
                else:
                    row_dict['uuid'] = ''
                data.append(row_dict)

            return jsonify({
                "code": 200,
                "msg": "success",
                "data": data
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("get file failed!"),
            "data": None
        }), 500


# ============== 账号登录 API ==============

# 平台 ID 映射
PLATFORM_IDS = {
    'xhs': 1,
    'shipinhao': 2,
    'douyin': 3,
    'kuaishou': 4,
    'bilibili': 5,
}

PLATFORM_NAMES = {
    1: '小红书',
    2: '视频号', 
    3: '抖音',
    4: '快手',
    5: 'B站',
}


@app.route("/api/startLogin", methods=['POST'])
def startLogin():
    """启动平台登录流程（使用 UserDataDir）"""
    import subprocess
    import logging
    import sys
    
    # 强制 print 输出到控制台 (绕过任何重定向)
    print("DEBUG: startLogin function entered", file=sys.__stdout__, flush=True)

    logger = logging.getLogger(__name__)
    
    data = request.get_json() or {}
    platform_str = data.get('platform', '').lower()
    account_name = data.get('accountName', '')
    
    # 使用 sys.__stdout__ 确保直接写到终端 fd=1
    print(f"DEBUG: startLogin called with platform={platform_str}, accountName={account_name}", file=sys.__stdout__, flush=True)
    logger.info(f"📥 收到登录请求: platform={platform_str}, accountName={account_name}")
    
    if not platform_str:
        return jsonify({"code": 400, "msg": "请选择平台", "data": None}), 400
    
    if platform_str not in PLATFORM_IDS:
        return jsonify({"code": 400, "msg": f"不支持的平台: {platform_str}", "data": None}), 400
    
    platform_id = PLATFORM_IDS[platform_str]
    
    # 生成唯一账号 ID（使用账号名称，避免平台名重复）
    # 清理账号名称中的特殊字符，确保文件夹名合法
    import re
    safe_account_name = re.sub(r'[^\w\u4e00-\u9fff-]', '', account_name) if account_name else 'user'
    account_id = f"{safe_account_name}_{uuid.uuid4().hex[:8]}"
    
    # 获取 profile_dir 路径
    profile_dir = get_profile_dir(platform_id, account_id)
    
    # 详细调试：打印路径信息
    print(f"DEBUG: profile_dir = {profile_dir}", file=sys.__stdout__, flush=True)
    print(f"DEBUG: profile_dir.exists() = {profile_dir.exists()}", file=sys.__stdout__, flush=True)
    print(f"DEBUG: profile_dir.parent = {profile_dir.parent}", file=sys.__stdout__, flush=True)
    
    logger.info(f"📁 生成账号目录: {profile_dir}")
    
    # 平台 URL
    PLATFORM_URLS = {
        'douyin': 'https://creator.douyin.com/',
        'xhs': 'https://creator.xiaohongshu.com/',
        'kuaishou': 'https://cp.kuaishou.com/',
        'bilibili': 'https://member.bilibili.com/',
        'shipinhao': 'https://channels.weixin.qq.com/login.html',
    }
    url = PLATFORM_URLS.get(platform_str, '')
    
    def run_login_in_background():
        """在后台线程中运行登录"""
        try:
            # 使用配置的 Chrome 路径打开登录页面
            chrome_args = [
                LOCAL_CHROME_PATH,
                f'--user-data-dir={profile_dir}',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions',
                '--lang=zh-CN',
                '--start-maximized',
                '--window-size=1280,800',
                url
            ]
            
            logger.info(f"🚀 启动登录: {platform_str} -> {profile_dir}")
            logger.info(f"   Chrome 路径: {LOCAL_CHROME_PATH}")
            logger.info(f"   目标 URL: {url}")
            
            # 检查 Chrome 路径
            if not Path(LOCAL_CHROME_PATH).exists():
                logger.error(f"❌ Chrome 路径不存在: {LOCAL_CHROME_PATH}")
                return
            
            # 启动 Chrome 进程（用户关闭浏览器后继续）
            logger.info(f"🌐 正在启动 Chrome 浏览器...")
            process = subprocess.Popen(chrome_args)
            logger.info(f"⏳ 等待用户完成登录并关闭浏览器...")
            process.wait()
            
            logger.info(f"✅ Chrome 已关闭，开始验证登录状态...")
            
            # 使用 auth.py 的 check_cookie 进行真实登录验证
            # (会启动浏览器访问页面，检测是否出现登录元素)
            import asyncio
            try:
                logger.info(f"🔍 正在验证 Cookies...")
                login_success = asyncio.run(check_cookie(platform_id, str(profile_dir)))
                logger.info(f"🔍 Cookie 验证结果: {'成功' if login_success else '失败'}")
            except Exception as verify_err:
                logger.error(f"⚠️ 登录验证出错: {verify_err}")
                login_success = False
            
            if login_success:
                # 写入数据库
                user_name = account_name or f"{PLATFORM_NAMES.get(platform_id, '未知')}账号"
                try:
                    conn = get_optimized_connection()
                    cursor = conn.cursor()
                    
                    # 检查是否已存在 (使用 type 和 userName 字段)
                    cursor.execute("SELECT id FROM user_info WHERE type=? AND userName=?", (platform_id, user_name))
                    existing = cursor.fetchone()
                    
                    if existing:
                        logger.warning(f"⚠️ 账号已存在: {user_name}")
                    else:
                        cursor.execute(
                            "INSERT INTO user_info (type, filePath, userName, status) VALUES (?, ?, ?, ?)",
                            (platform_id, str(profile_dir), user_name, 1)
                        )
                        conn.commit()
                        logger.info(f"✅ 账号添加成功: {user_name} -> {platform_str} (ID={cursor.lastrowid})")
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"❌ 数据库操作失败: {e}")

            else:
                logger.warning(f"⚠️ 登录验证失败，未检测到有效 Cookies，不添加账号")
                # 清理无效的 profile_dir，避免产生孤儿文件夹
                import shutil
                try:
                    if profile_dir.exists():
                        shutil.rmtree(profile_dir)
                        logger.info(f"🧹 已清理无效的 profile 目录: {profile_dir.name}")
                except Exception as cleanup_err:
                    logger.warning(f"⚠️ 清理 profile 目录失败: {cleanup_err}")
        
        except Exception as e:
            logger.error(f"❌ 登录过程出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # 在后台线程中运行
    login_thread = threading.Thread(target=run_login_in_background, daemon=True)
    login_thread.start()
    
    logger.info(f"📤 登录线程已启动，等待用户操作...")
    
    return jsonify({
        "code": 200,
        "msg": f"正在打开 {PLATFORM_NAMES.get(platform_id, platform_str)} 登录页面，请在浏览器中完成登录后关闭浏览器",
        "data": {
            "account_id": account_id,
            "profile_dir": str(profile_dir),
            "platform": platform_str,
            "platform_id": platform_id
        }
    }), 200


@app.route("/api/openBrowser", methods=['POST'])
def openBrowser():
    """打开账号对应的 UserDataDir 浏览器，用于手动操作增加使用痕迹"""
    import subprocess
    from utils.global_state import is_account_locked, acquire_account_lock, release_account_lock
    
    data = request.get_json() or {}
    account_id = data.get('accountId')
    
    if not account_id:
        return jsonify({"code": 400, "msg": "缺少 accountId 参数", "data": None}), 400
    
    # 检查账号是否被占用
    lock_info = is_account_locked(account_id)
    if lock_info:
        task_type_names = {
            'ai_publish': 'AI自动发布任务',
            'rpa_publish': 'RPA发布任务',
            'manual_browser': '手动浏览器操作'
        }
        task_name = task_type_names.get(lock_info.get('task_type'), '其他任务')
        return jsonify({
            "code": 409, 
            "msg": f"该账号正在被 {task_name} 占用，请稍后再试", 
            "data": {"locked_by": lock_info}
        }), 409
    
    try:
        # 从数据库获取账号信息
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT filePath, type FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({"code": 404, "msg": "账号不存在", "data": None}), 404
            
            profile_dir = result[0]
            platform_type = result[1]
        
        # 平台首页 URL
        PLATFORM_URLS = {
            1: 'https://creator.xiaohongshu.com/',  # 小红书
            2: 'https://channels.weixin.qq.com/platform/',    # 视频号（已登录后打开首页）
            3: 'https://creator.douyin.com/',        # 抖音
            4: 'https://cp.kuaishou.com/',           # 快手
            5: 'https://member.bilibili.com/',       # B站
        }
        url = PLATFORM_URLS.get(platform_type, 'https://www.baidu.com')
        
        def run_browser_in_background():
            """在后台线程中运行浏览器"""
            # 获取账号锁
            acquire_account_lock(account_id, 'manual_browser', f'browser_{account_id}')
            try:
                # 获取 Chrome 路径
                chrome_path = LOCAL_CHROME_PATH
                
                # 检查 Chrome 是否存在
                if not Path(chrome_path).exists():
                    print(f"❌ Chrome 路径不存在: {chrome_path}")
                    return
                
                chrome_args = [
                    chrome_path,
                    f'--user-data-dir={profile_dir}',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--lang=zh-CN',
                    '--start-maximized',
                    '--window-size=1280,800',
                    url
                ]
                
                print(f"🌐 打开浏览器: 账号 {account_id}")
                print(f"   Chrome 路径: {chrome_path}")
                print(f"   Profile 目录: {profile_dir}")
                print(f"   目标 URL: {url}")
                
                # 启动 Chrome 浏览器（不要使用 CREATE_NO_WINDOW，否则窗口不显示）
                process = subprocess.Popen(chrome_args)
                
                # 等待进程结束（用户关闭浏览器）
                process.wait()
                
                print(f"✅ 浏览器已关闭: 账号 {account_id}")
                
            except FileNotFoundError as e:
                print(f"❌ 找不到 Chrome: {e}")
                print(f"   请检查 Chrome 路径配置: {LOCAL_CHROME_PATH}")
            except Exception as e:
                print(f"❌ 打开浏览器失败: {e}")
                import traceback
                print(traceback.format_exc())
            finally:
                # 释放账号锁
                release_account_lock(account_id)
        
        # 在后台线程中运行
        browser_thread = threading.Thread(target=run_browser_in_background, daemon=True)
        browser_thread.start()
        
        return jsonify({
            "code": 200,
            "msg": "浏览器已打开，请在浏览器中进行正常操作。关闭浏览器后操作痕迹会自动保存。",
            "data": {"account_id": account_id, "profile_dir": profile_dir}
        }), 200
        
    except Exception as e:
        print(f"❌ 打开浏览器失败: {e}")
        return jsonify({"code": 500, "msg": f"打开浏览器失败: {e}", "data": None}), 500


@app.route("/getAccounts", methods=['GET'])
def getAccounts():
    """快速获取所有账号信息，不进行cookie验证"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM user_info''')
            rows = cursor.fetchall()
            rows_list = [list(row) for row in rows]

            print("\n📋 当前数据表内容（快速获取）：")
            for row in rows:
                print(row)

            return jsonify(
                {
                    "code": 200,
                    "msg": None,
                    "data": rows_list
                }), 200
    except Exception as e:
        print(f"获取账号列表时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"获取账号列表失败: {str(e)}",
            "data": None
        }), 500


# 缓存配置（秒）
CACHE_DURATION = VALIDATION_INTERVAL_SECONDS
CHECK_CACHE = {}  # 存储账号最后验证时间 {account_id: timestamp}


def update_cookie_validation(cursor, account_id: int, is_valid: bool):
    """更新账号的 Cookie 验证状态和时间戳"""
    new_status = 1 if is_valid else 0
    cursor.execute('''
        UPDATE user_info 
        SET status = ?, last_validated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (new_status, account_id))


@app.route("/getValidAccounts", methods=['GET'])
async def getValidAccounts():
    """获取所有账号并验证 Cookie 状态（使用数据库持久化缓存）"""
    force_sync = request.args.get('force', 'false').lower() == 'true'
    
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, type, filePath, userName, status, last_validated_at FROM user_info')
        rows = cursor.fetchall()
        rows_list = [list(row) for row in rows]
        
        print("\n📋 当前数据表内容：")
        for row in rows:
            print(row)
            
        for row in rows_list:
            account_id = row[0]
            
            # 使用数据库持久化缓存判断
            cache_valid = is_cache_valid(account_id, CACHE_DURATION) if not force_sync else False
            
            if not cache_valid:
                # 缓存失效或强制刷新，执行验证
                flag = await check_cookie(row[1], row[2])
                update_cookie_validation(cursor, account_id, flag)
                conn.commit()
                
                if not flag:
                    row[4] = 0
                    print(f"❌ 用户 {account_id} 状态已更新为失效")
                else:
                    row[4] = 1
                    print(f"✅ 用户 {account_id} 状态已更新为有效")
            else:
                # 使用缓存
                last_validated = get_last_validated_time(account_id)
                if last_validated:
                    elapsed = (datetime.now() - last_validated).total_seconds()
                    remaining = int(CACHE_DURATION - elapsed)
                    print(f"📦 使用缓存: 账号 {account_id}, 剩余有效期 {remaining}秒")

        return jsonify({
            "code": 200,
            "msg": None,
            "data": rows_list
        }), 200


@app.route("/api/syncAccountStatus/<int:account_id>", methods=['POST'])
async def sync_single_account_status(account_id):
    """同步单个账号的登录状态"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT id, type, filePath, userName, status FROM user_info WHERE id = ?', (account_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({
                    "code": 404,
                    "msg": "账号不存在",
                    "data": None
                }), 404
            
            # 执行cookie验证
            is_valid = await check_cookie(row['type'], row['filePath'])
            new_status = 1 if is_valid else 0
            
            # 更新数据库
            cursor.execute('UPDATE user_info SET status = ?, last_validated_at = ? WHERE id = ?', 
                          (new_status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), account_id))
            conn.commit()
            
            status_text = "有效" if is_valid else "失效"
            print(f"{'✅' if is_valid else '❌'} 账号 {account_id} 状态同步完成: {status_text}")
            
            return jsonify({
                "code": 200,
                "msg": f"账号状态已同步: {status_text}",
                "data": {"id": account_id, "status": new_status, "is_valid": is_valid}
            }), 200
            
    except Exception as e:
        print(f"❌ 同步账号 {account_id} 状态失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"同步失败: {str(e)}",
            "data": None
        }), 500

@app.route('/deleteFile', methods=['GET'])
def delete_file():
    file_id = request.args.get('id')

    if not file_id or not file_id.isdigit():
        return jsonify({
            "code": 400,
            "msg": "Invalid or missing file ID",
            "data": None
        }), 400

    try:
        # 获取数据库连接
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404

            record = dict(record)

            # 获取文件路径并删除实际文件
            file_path = Path(RUNTIME_DIR / "data/videos" / record['file_path'])
            if file_path.exists():
                try:
                    file_path.unlink()  # 删除文件
                    print(f"✅ 实际文件已删除: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除实际文件失败: {e}")
                    # 即使删除文件失败，也要继续删除数据库记录，避免数据不一致
            else:
                print(f"⚠️ 实际文件不存在: {file_path}")

            # 删除数据库记录
            cursor.execute("DELETE FROM file_records WHERE id = ?", (file_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "File deleted successfully",
            "data": {
                "id": record['id'],
                "filename": record['filename']
            }
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500

@app.route('/renameFile', methods=['POST'])
def rename_file():
    """重命名视频文件"""
    data = request.get_json()
    file_id = data.get('id')  
    new_filename = data.get('filename')
    
    if not file_id or not new_filename:
        return jsonify({
            "code": 400,
            "msg": "Missing file ID or new filename",
            "data": None
        }), 400
    
    # 验证文件名安全性
    if '..' in new_filename or '/' in new_filename or '\\' in new_filename:
        return jsonify({
            "code": 400,
            "msg": "Invalid filename",
            "data": None
        }), 400
    
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 查询文件记录
            cursor.execute("SELECT * FROM file_records WHERE id = ?", (file_id,))
            record = cursor.fetchone()
            
            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "File not found",
                    "data": None
                }), 404
            
            record = dict(record)
            old_file_path = record['file_path']
            
            # 从旧路径中提取 UUID
            uuid_part = old_file_path.split('_', 1)[0] if '_' in old_file_path else ''
            
            # 获取文件扩展名
            old_extension = old_file_path.split('.')[-1] if '.' in old_file_path else ''
            
            # 确保新文件名有扩展名
            if '.' not in new_filename and old_extension:
                new_filename = f"{new_filename}.{old_extension}"
            
            # 构造新的文件路径 (保留 UUID)
            new_file_path = f"{uuid_part}_{new_filename}" if uuid_part else new_filename
            
            # 物理文件重命名
            old_physical_path = Path(RUNTIME_DIR / "data/videos" / old_file_path)
            new_physical_path = Path(RUNTIME_DIR / "data/videos" / new_file_path)
            
            if old_physical_path.exists():
                old_physical_path.rename(new_physical_path)
                print(f"✅ 文件已重命名: {old_file_path} -> {new_file_path}")
            else:
                print(f" ⚠️ 物理文件不存在: {old_physical_path}")
            
            # 更新数据库记录
            cursor.execute(
                "UPDATE file_records SET filename = ?, file_path = ? WHERE id = ?",
                (new_filename, new_file_path, file_id)
            )
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "File renamed successfully",
                "data": {
                    "id": file_id,
                    "filename": new_filename,
                    "file_path": new_file_path
                }
            }), 200
            
    except Exception as e:
        print(f"重命名失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"Rename failed: {str(e)}",
            "data": None
        }), 500

@app.route('/deleteAccount', methods=['GET'])
def delete_account():
    import shutil
    account_id = int(request.args.get('id'))

    try:
        # 获取数据库连接
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询要删除的记录
            cursor.execute("SELECT * FROM user_info WHERE id = ?", (account_id,))
            record = cursor.fetchone()

            if not record:
                return jsonify({
                    "code": 404,
                    "msg": "account not found",
                    "data": None
                }), 404

            record = dict(record)
            profile_dir = record.get('filePath', '')
            
            # 删除 UserDataDir 文件夹
            if profile_dir and Path(profile_dir).exists():
                try:
                    shutil.rmtree(profile_dir)
                    print(f"✅ 已删除 UserDataDir: {profile_dir}")
                except Exception as e:
                    print(f"⚠️ 删除 UserDataDir 失败: {e}")

            # 删除数据库记录
            cursor.execute("DELETE FROM user_info WHERE id = ?", (account_id,))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account deleted successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("delete failed!"),
            "data": None
        }), 500


# 验证码SSE通知接口
@app.route('/verificationCodeNotify')
def verification_code_notify():
    """SSE接口，用于向前端推送验证码需求通知"""
    task_id = request.args.get('taskId')
    if not task_id:
        return jsonify({"code": 400, "msg": "缺少taskId参数"}), 400
    
    status_queue = Queue()
    active_queues[f"verify_{task_id}"] = status_queue
    
    def on_close():
        print(f"清理验证码队列: verify_{task_id}")
        if f"verify_{task_id}" in active_queues:
            del active_queues[f"verify_{task_id}"]
    
    response = Response(sse_stream(status_queue), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Connection'] = 'keep-alive'
    return response

# 提交验证码接口
@app.route('/submitVerificationCode', methods=['POST'])
def submit_verification_code():
    """接收用户输入的验证码并传递给上传任务，等待验证结果"""
    data = request.get_json()
    task_id = data.get('taskId')
    code = data.get('code')
    
    if not task_id or not code:
        return jsonify({"code": 400, "msg": "缺少taskId或code参数"}), 400
    
    # 将验证码放入对应任务的队列
    if task_id in verification_queues:
        verification_queues[task_id].put(code)
        
        # 等待验证结果（通过 active_queues 通知）
        verify_notify_key = f"verify_{task_id}"
        if verify_notify_key in active_queues:
            try:
                # 等待验证结果，最多 30 秒
                result = active_queues[verify_notify_key].get(timeout=30)
                if result == "VERIFICATION_SUCCESS":
                    return jsonify({"code": 200, "msg": "验证码验证成功", "data": {"status": "success"}}), 200
                elif result == "VERIFICATION_FAILED":
                    return jsonify({"code": 200, "msg": "验证码错误，请重新输入", "data": {"status": "failed"}}), 200
                else:
                    return jsonify({"code": 200, "msg": "验证码已提交", "data": {"status": "unknown"}}), 200
            except Exception:
                return jsonify({"code": 200, "msg": "验证码已提交，等待验证结果超时", "data": {"status": "timeout"}}), 200
        else:
            return jsonify({"code": 200, "msg": "验证码已提交"}), 200
    else:
        return jsonify({"code": 404, "msg": "未找到对应的任务"}), 404

@app.route('/postVideo', methods=['POST'])
def postVideo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取参数
    file_list = data.get('fileList', [])
    title = data.get('title')
    description = data.get('description', '')
    tags = data.get('tags', [])
    category = data.get('category')
    enableTimer = data.get('enableTimer', False)
    if category == 0:
        category = None
    thumbnail_path = data.get('thumbnail', '')
    is_draft = data.get('isDraft', False)

    videos_per_day = data.get('videosPerDay')
    daily_times = data.get('dailyTimes')
    start_days = data.get('startDays')
    
    # 【新增】支持多平台参数，兼容旧格式
    platforms = data.get('platforms')
    accounts_by_platform = data.get('accountsByPlatform', {})
    
    # 兼容旧的单平台格式
    if platforms is None:
        single_type = data.get('type')
        account_list = data.get('accountList', [])
        if single_type is not None:
            platforms = [single_type]
            accounts_by_platform = {str(single_type): account_list}
        else:
            return jsonify({"code": 400, "msg": "缺少平台参数"}), 400
    
    # 确保 platforms 是列表
    if isinstance(platforms, int):
        platforms = [platforms]
    
    print(f"📤 多平台发布请求: platforms={platforms}, accounts_by_platform={accounts_by_platform}")
    
    task_ids = []
    
    # 为每个平台创建独立的发布任务
    for platform in platforms:
        platform_key = str(platform)
        account_list = accounts_by_platform.get(platform_key, [])
        
        if not account_list:
            print(f"⚠️ 平台 {platform} 没有选择账号，跳过")
            continue
        
        # 将 account_list（ID 列表）转换为 profile_dir 路径列表
        profile_dirs = []
        invalid_accounts = []
        
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            for account_id in account_list:
                cursor.execute('SELECT filePath, type FROM user_info WHERE id = ?', (account_id,))
                result = cursor.fetchone()
                if result:
                    file_path = result[0]
                    acc_platform = result[1]
                    
                    profile_dir = Path(file_path) if file_path else get_profile_dir(acc_platform, str(account_id))
                    
                    # 检查 Chrome 是否正在使用
                    if is_chrome_using_profile(profile_dir):
                        return jsonify({
                            "code": 409,
                            "msg": f"账号 {account_id} 的浏览器正在使用中，请先关闭浏览器后再发布",
                            "data": {"locked_account_id": account_id}
                        }), 409
                    
                    # 检查缓存有效性
                    if is_cache_valid(account_id, CACHE_DURATION):
                        print(f"📦 使用缓存: 账号 {account_id}")
                    else:
                        print(f"🔍 检查 profile_dir: {profile_dir}")
                        if not profile_dir.exists():
                            invalid_accounts.append(account_id)
                            print(f"❌ 账号 {account_id} 尚未登录（profile_dir 不存在）")
                            continue
                        update_cookie_validation(cursor, account_id, True)
                        conn.commit()
                        print(f"✅ 账号 {account_id} profile_dir 存在")
                    
                    profile_dirs.append(str(profile_dir))
                else:
                    print(f"⚠️ 账号 ID {account_id} 未找到")
        
        if not profile_dirs:
            if invalid_accounts:
                print(f"⚠️ 平台 {platform} 所有账号都失效")
            continue
        
        # 为当前平台创建任务记录
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO publish_tasks (
                        task_type, platform, title, description, tags, 
                        video_path, account_ids, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'manual', platform, title, description, 
                    json.dumps(tags, ensure_ascii=False),
                    file_list[0] if file_list else '',
                    json.dumps(account_list),
                    'running'
                ))
                conn.commit()
                publish_task_id = cursor.lastrowid
                task_ids.append(publish_task_id)
        except Exception as e:
            print(f"创建平台 {platform} 任务失败: {e}")
            continue

        # 启动异步发布（带超时控制）
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        
        RPA_TIMEOUT_SECONDS = 180  # 3 分钟
        
        def execute_publish_for_platform(p_type, p_profile_dirs, p_task_id):
            """为特定平台执行发布"""
            match p_type:
                case 1:
                    post_video_xhs(title, file_list, tags, p_profile_dirs, category, enableTimer, videos_per_day, daily_times, start_days, description, f"manual_{p_task_id}")
                case 2:
                    post_video_tencent(title, file_list, tags, p_profile_dirs, category, enableTimer, videos_per_day, daily_times, start_days, is_draft, f"manual_{p_task_id}", description)
                case 3:
                    post_video_DouYin_with_taskid(title, file_list, tags, p_profile_dirs, category, enableTimer, videos_per_day, daily_times, start_days, thumbnail_path, description, f"manual_{p_task_id}")
                case 4:
                    post_video_ks(title, file_list, tags, p_profile_dirs, category, enableTimer, videos_per_day, daily_times, start_days, description, f"manual_{p_task_id}")
                case 5:
                    post_video_bilibili(title, file_list, tags, p_profile_dirs, category, enableTimer, videos_per_day, daily_times, start_days, description, f"manual_{p_task_id}")
        
        def run_publish_with_timeout(p_type, p_profile_dirs, p_task_id):
            """带超时控制的发布任务执行"""
            import time
            start_time = time.time()
            
            try:
                print(f"📤 开始执行平台 {p_type} 发布任务 ID={p_task_id}，超时时间={RPA_TIMEOUT_SECONDS}秒")
                
                with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"rpa_task_{p_task_id}") as executor:
                    future = executor.submit(execute_publish_for_platform, p_type, p_profile_dirs, p_task_id)
                    try:
                        future.result(timeout=RPA_TIMEOUT_SECONDS)
                        elapsed = int(time.time() - start_time)
                        print(f"✅ 平台 {p_type} 发布任务 ID={p_task_id} 完成，耗时 {elapsed} 秒")
                        
                        with sqlite3.connect(DATABASE_PATH) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                'UPDATE publish_tasks SET status = ?, progress = 100, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                                ('completed', p_task_id)
                            )
                            conn.commit()
                            
                    except FuturesTimeoutError:
                        elapsed = int(time.time() - start_time)
                        error_msg = f"发布任务超时: 执行时间超过 {RPA_TIMEOUT_SECONDS} 秒（{elapsed} 秒）"
                        print(f"❌ {error_msg}")
                        future.cancel()
                        
                        with sqlite3.connect(DATABASE_PATH) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                'UPDATE publish_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                                ('failed', error_msg, p_task_id)
                            )
                            conn.commit()
                            
            except Exception as e:
                error_msg = str(e)
                elapsed = int(time.time() - start_time)
                print(f"❌ 平台 {p_type} 发布任务执行失败 (耗时 {elapsed}秒): {error_msg}")
                
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE publish_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                        ('failed', error_msg, p_task_id)
                    )
                    conn.commit()

        # 为当前平台启动后台线程
        threading.Thread(
            target=run_publish_with_timeout, 
            args=(platform, profile_dirs, publish_task_id),
            daemon=True, 
            name=f"publish_task_{publish_task_id}"
        ).start()
        print(f"✅ 平台 {platform} 任务 ID={publish_task_id} 已提交到后台")

    if not task_ids:
        return jsonify({
            "code": 400,
            "msg": "没有有效的发布任务，请检查账号状态",
            "data": None
        }), 400

    return jsonify({
        "code": 200,
        "msg": f"已创建 {len(task_ids)} 个发布任务",
        "data": {"taskIds": task_ids}
    }), 200


@app.route('/updateUserinfo', methods=['POST'])
def updateUserinfo():
    # 获取JSON数据
    data = request.get_json()

    # 从JSON数据中提取 type 和 userName
    user_id = data.get('id')
    type = data.get('type')
    userName = data.get('userName')
    try:
        # 获取数据库连接
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 更新数据库记录
            cursor.execute('''
                           UPDATE user_info
                           SET type     = ?,
                               userName = ?
                           WHERE id = ?;
                           ''', (type, userName, user_id))
            conn.commit()

        return jsonify({
            "code": 200,
            "msg": "account update successfully",
            "data": None
        }), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": str("update failed!"),
            "data": None
        }), 500

@app.route('/postVideoBatch', methods=['POST'])
def postVideoBatch():
    data_list = request.get_json()

    if not isinstance(data_list, list):
        return jsonify({"error": "Expected a JSON array"}), 400
    for data in data_list:
        # 从JSON数据中提取fileList和accountList
        file_list = data.get('fileList', [])
        account_list = data.get('accountList', [])
        type = data.get('type')
        title = data.get('title')
        tags = data.get('tags')
        category = data.get('category')
        enableTimer = data.get('enableTimer')
        if category == 0:
            category = None
        productLink = data.get('productLink', '')
        productTitle = data.get('productTitle', '')

        videos_per_day = data.get('videosPerDay')
        daily_times = data.get('dailyTimes')
        start_days = data.get('startDays')
        
        # 将 account_list 转换为 profile_dir 路径列表
        profile_dirs = []
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            for account_id in account_list:
                cursor.execute('SELECT filePath, type FROM user_info WHERE id = ?', (account_id,))
                result = cursor.fetchone()
                if result:
                    file_path = result[0]
                    platform = result[1]
                    # 直接使用数据库中存储的 profile_dir 路径
                    profile_dir = Path(file_path) if file_path else get_profile_dir(platform, str(account_id))
                    profile_dirs.append(str(profile_dir))
        
        print("File List:", file_list)
        print("Profile Dirs:", profile_dirs)
        match type:
            case 1:
                return
            case 2:
                post_video_tencent(title, file_list, tags, profile_dirs, category, enableTimer, videos_per_day, daily_times,
                                   start_days)
            case 3:
                post_video_DouYin(title, file_list, tags, profile_dirs, category, enableTimer, videos_per_day, daily_times,
                          start_days, productLink, productTitle)
            case 4:
                post_video_ks(title, file_list, tags, profile_dirs, category, enableTimer, videos_per_day, daily_times,
                          start_days, '')
            case 5:
                post_video_bilibili(title, file_list, tags, profile_dirs, category, enableTimer, videos_per_day, daily_times,
                          start_days, '')
    # 返回响应给客户端
    return jsonify(
        {
            "code": 200,
            "msg": None,
            "data": None
        }), 200

# Cookie文件上传API
@app.route('/uploadCookie', methods=['POST'])
def upload_cookie():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 500,
                "msg": "没有找到Cookie文件",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 500,
                "msg": "Cookie文件名不能为空",
                "data": None
            }), 400

        if not file.filename.endswith('.json'):
            return jsonify({
                "code": 500,
                "msg": "Cookie文件必须是JSON格式",
                "data": None
            }), 400

        # 获取账号信息
        account_id = request.form.get('id')
        platform = request.form.get('platform')

        if not account_id or not platform:
            return jsonify({
                "code": 500,
                "msg": "缺少账号ID或平台信息",
                "data": None
            }), 400

        # 从数据库获取账号的文件路径
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT filePath FROM user_info WHERE id = ?', (account_id,))
            result = cursor.fetchone()

        if not result:
            return jsonify({
                "code": 500,
                "msg": "账号不存在",
                "data": None
            }), 404

        # 保存上传的Cookie文件到对应路径
        cookie_file_path = Path(BASE_DIR / "data/cookies" / result['filePath'])
        cookie_file_path.parent.mkdir(parents=True, exist_ok=True)

        file.save(str(cookie_file_path))

        # 更新数据库中的账号信息（可选，比如更新更新时间）
        # 这里可以根据需要添加额外的处理逻辑

        return jsonify({
            "code": 200,
            "msg": "Cookie文件上传成功",
            "data": None
        }), 200

    except Exception as e:
        print(f"上传Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"上传Cookie文件失败: {str(e)}",
            "data": None
        }), 500


# Cookie文件下载API
@app.route('/downloadCookie', methods=['GET'])
def download_cookie():
    try:
        file_path = request.args.get('filePath')
        if not file_path:
            return jsonify({
                "code": 500,
                "msg": "缺少文件路径参数",
                "data": None
            }), 400

        # 验证文件路径的安全性，防止路径遍历攻击
        cookie_file_path = Path(BASE_DIR / "data/cookies" / file_path).resolve()
        base_path = Path(BASE_DIR / "data/cookies").resolve()

        if not cookie_file_path.is_relative_to(base_path):
            return jsonify({
                "code": 500,
                "msg": "非法文件路径",
                "data": None
            }), 400

        if not cookie_file_path.exists():
            return jsonify({
                "code": 500,
                "msg": "Cookie文件不存在",
                "data": None
            }), 404

        # 返回文件
        return send_from_directory(
            directory=str(cookie_file_path.parent),
            path=cookie_file_path.name,
            as_attachment=True
        )

    except Exception as e:
        print(f"下载Cookie文件时出错: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"下载Cookie文件失败: {str(e)}",
            "data": None
        }), 500

# ============== Persona Management APIs ==============

@app.route('/api/personas', methods=['GET'])
def get_personas():
    try:
        lang = normalize_persona_lang(request.args.get('lang', 'zh-CN'))
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM platform_personas WHERE language = ?", (lang,))
            rows = cursor.fetchall()
            
            data = {}
            for row in rows:
                code = row['platform_code']
                data[code] = {
                    "code": code,
                    "name": row['platform_name'],
                    "prompt": row['persona_prompt'],
                    "ui_data": json.loads(row['ui_data']) if row['ui_data'] else {}
                }
            return jsonify({"code": 200, "msg": "Success", "data": data}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/api/personas/update', methods=['POST'])
def update_persona():
    data = request.get_json()
    code = data.get('code')
    lang = normalize_persona_lang(data.get('lang') or request.args.get('lang', 'zh-CN'))
    ui_data = data.get('ui_data') # Expecting dict

    if not code:
        return jsonify({"code": 400, "msg": "Missing platform code"}), 400

    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # Reconstruct prompt if ui_data is present
            new_prompt = None
            if ui_data:
                # Helper to safely join list or string
                def fmt_list(val):
                    if isinstance(val, list):
                        return ", ".join(val)
                    return str(val)

                name = ui_data.get('name', code)
                features = ui_data.get('features', {})
                desc = ui_data.get('description', '')
                hot_topics = ui_data.get('hot_topics', '') # New field

                # Construct prompt based on platform type (template matching platform_personas.py style)
                # We can make a generic template or specific ones. For simplicity and robustness, we use a generic structure that fits all.
                
                if lang == "en":
                    prompt_lines = [
                        f"### {name} Audience Profile and Content Style:",
                        "",
                        "**Audience Segments:**",
                        f"{features.get('users', '')}",
                        "",
                        "**Content Style Requirements:**",
                        f"{features.get('style', '')}",
                    ]
                    trends_header = "**Recent Hot Topics / Trends:**"
                    keywords_header = "**Content Keywords:**"
                    keyword_joiner = ", "
                else:
                    prompt_lines = [
                        f"### {name} 用户画像与内容风格：",
                        "",
                        "**用户群体：**",
                        f"{features.get('users', '')}", 
                        "",
                        "**内容风格要求：**",
                        f"{features.get('style', '')}",
                    ]
                    trends_header = "**近期热点/流行趋势 (Trends)：**"
                    keywords_header = "**内容关键词：**"
                    keyword_joiner = "、"
                
                if hot_topics:
                     prompt_lines.append("")
                     prompt_lines.append(trends_header)
                     prompt_lines.append(f"{hot_topics}")

                prompt_lines.append("")
                prompt_lines.append(keywords_header)
                # Format keywords as a string if it's a list
                keywords = features.get('keywords', [])
                if isinstance(keywords, list):
                    keywords_str = keyword_joiner.join(keywords)
                else:
                    keywords_str = str(keywords)
                prompt_lines.append(f"{keywords_str}")

                new_prompt = "\n".join(prompt_lines)

            # Update DB
            updates = []
            values = []

            if new_prompt is not None:
                updates.append("persona_prompt = ?")
                values.append(new_prompt)

            if ui_data is not None:
                updates.append("ui_data = ?")
                values.append(json.dumps(ui_data, ensure_ascii=False))

            if not updates:
                return jsonify({"code": 200, "msg": "Nothing to update"}), 200

            values.extend([lang, code])
            sql = f"UPDATE platform_personas SET {', '.join(updates)} WHERE language = ? AND platform_code = ?"
            cursor.execute(sql, values)
            conn.commit()

            return jsonify({"code": 200, "msg": "Persona updated successfully"}), 200
    except Exception as e:
        print(f"Error updating persona: {e}")
        return jsonify({"code": 500, "msg": str(e)}), 500

# ============== AI 创作接口 ==============

@app.route('/api/create_prompt', methods=['POST'])
def create_prompt():
    """
    AI 文案生成接口 (异步任务模式) - 支持多平台
    输入: topic, platforms, accounts_by_platform, style, use_mock, count, llm_config
    输出: task_ids (立即返回，后台异步执行LLM调用)
    """
    import json as json_lib
    data = request.get_json()
    topic = data.get('topic')
    
    if not topic:
        return jsonify({"code": 400, "msg": "缺少 topic 参数", "data": None}), 400
    
    # 【新增】支持多平台参数，兼容旧格式
    platforms = data.get('platforms')
    accounts_by_platform = data.get('accounts_by_platform', {})
    
    # 兼容旧的单平台格式
    if platforms is None:
        single_platform = data.get('platform', 'douyin')
        account_id = data.get('account_id')
        platforms = [single_platform]
        if account_id:
            accounts_by_platform = {single_platform: [account_id]}
    
    # 确保 platforms 是列表
    if isinstance(platforms, str):
        platforms = [platforms]
    
    style = data.get('style', '产品展示')
    use_mock = data.get('use_mock', False)
    count = int(data.get('count', 1))
    auto_publish = data.get('auto_publish', False)
    
    # 平台映射
    platform_map = {'douyin': 3, 'xhs': 1, 'ks': 4, 'wx': 2, 'bilibili': 5}
    
    # LLM 配置
    llm_config = data.get('llm_config', {})
    base_url = llm_config.get('llmBaseUrl') or os.getenv('LLM_BASE_URL')
    api_key = llm_config.get('llmApiKey') or os.getenv('LLM_API_KEY')
    model = llm_config.get('llmModel') or 'gpt-4o'
    
    print(f"📤 多平台AI获客请求: platforms={platforms}, accounts_by_platform={accounts_by_platform}")
    
    task_ids = []
    
    try:
        # 为每个平台创建独立的任务
        for platform in platforms:
            platform_num = platform_map.get(platform, 3)
            platform_accounts = accounts_by_platform.get(platform, [])
            # 取第一个账号ID (用于单账号场景的兼容)
            account_id = platform_accounts[0] if platform_accounts else None
            
            # 创建任务记录
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # 确保表有新字段
                for col in ['prompt_results TEXT', 'selected_index INTEGER DEFAULT 0', 
                            'platform_str TEXT', 'style TEXT', 'account_id INTEGER', 
                            'platform INTEGER DEFAULT 3', 'auto_publish INTEGER DEFAULT 0',
                            'account_ids TEXT']:
                    try:
                        cursor.execute(f"ALTER TABLE creation_tasks ADD COLUMN {col}")
                    except sqlite3.OperationalError:
                        pass
                
                cursor.execute('''
                    INSERT INTO creation_tasks (topic, status, platform_str, style, account_id, platform, auto_publish, account_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (topic, 'prompt_pending', platform, style, account_id, platform_num, 
                      1 if auto_publish else 0, json_lib.dumps(platform_accounts)))
                conn.commit()
                task_id = cursor.lastrowid
                task_ids.append(task_id)
            
            print(f"✅ 平台 {platform} 文案生成任务已创建: ID={task_id}, topic={topic}")
            
            # 后台异步执行 LLM 调用
            def run_llm_generation(t_id, t_platform, t_topic, t_style, t_count, t_use_mock, t_base_url, t_api_key, t_model):
                try:
                    # 更新状态为 generating
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        cursor = conn.cursor()
                        cursor.execute('UPDATE creation_tasks SET status = ? WHERE id = ?', 
                                       ('prompt_generating', t_id))
                        conn.commit()
                    
                    # Mock 模式
                    if t_use_mock or not t_base_url or not t_api_key:
                        import time
                        time.sleep(0.5)
                        print(f"🎭 [Mock] 平台 {t_platform} 使用预设文案数据")
                        
                        mock_pool = [
                            {
                                "title": f"【{t_platform}爆款】一刀切开，热气腾腾的金黄红薯，瞬间点燃味蕾！",
                                "video_prompt": "清晨柔和的自然光洒在金黄的红薯田，农民挥动镰刀快速收割，手中满载新鲜红薯。镜头快速拉近到一只手把红薯从泥土中拔起，土壤颗粒飞溅，红薯表面呈现露珠光泽。",
                                "tags": [t_topic, "农产品", f"{t_platform}种草"],
                                "description": "看到热气了吗？快在评论里告诉我你最想配的酱料！",
                                "_mock": True
                            },
                            {
                                "title": f"从田间到餐桌，红薯甜品秒变网红美味！",
                                "video_prompt": "午后金色阳光透过稻草棚洒在农家小院，农妇手提装满红薯的竹篮走向厨房。",
                                "tags": [f"{t_topic}甜品", "厨房实拍", f"{t_platform}美食"],
                                "description": "想尝试这款红薯甜品吗？点赞并在评论里说出你的创意配料！",
                                "_mock": True
                            },
                            {
                                "title": f"红薯苗萌发瞬间，种下健康，收获丰收！",
                                "video_prompt": "清晨微雾笼罩的农田，柔和的晨光照在一排排整齐的红薯苗床上。",
                                "tags": [f"{t_topic}种植", "农业科技", f"{t_platform}生活"],
                                "description": "想在自家院子里种红薯吗？快在评论区留言你的种植计划！",
                                "_mock": True
                            }
                        ]
                        result = mock_pool[:t_count]
                    else:
                        # 真实 LLM 调用 - 获取对应平台的用户画像
                        persona_text = None
                        try:
                            with sqlite3.connect(DATABASE_PATH) as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT persona_prompt FROM platform_personas WHERE language = ? AND platform_code = ?",
                                    ("zh-CN", t_platform)
                                )
                                row = cursor.fetchone()
                                if row:
                                    persona_text = row[0]
                                    print(f"✅ 已获取平台 {t_platform} 用户画像")
                        except Exception as e:
                            print(f"Warning: Failed to fetch persona for {t_platform}: {e}")
                        
                        client = LLMClient(base_url=t_base_url, api_key=t_api_key, model=t_model)
                        result = generate_video_prompt(client, t_topic, t_platform, t_style, custom_persona=persona_text, count=t_count)
                    
                    # 保存结果
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE creation_tasks 
                            SET status = ?, prompt_results = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', ('prompt_completed', json_lib.dumps(result, ensure_ascii=False), t_id))
                        conn.commit()
                    
                    print(f"✅ 平台 {t_platform} 文案生成完成: task_id={t_id}, count={len(result)}")
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ 平台 {t_platform} 文案生成失败: {error_msg}")
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE creation_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                            ('prompt_failed', error_msg, t_id)
                        )
                        conn.commit()
            
            # 启动后台线程（绑定当前循环的变量）
            threading.Thread(
                target=run_llm_generation, 
                args=(task_id, platform, topic, style, count, use_mock, base_url, api_key, model),
                daemon=True
            ).start()
        
        return jsonify({
            "code": 200,
            "msg": f"已创建 {len(task_ids)} 个文案生成任务",
            "data": {"task_ids": task_ids, "status": "prompt_pending"}
        }), 200
        
    except Exception as e:
        print(f"创建任务失败: {e}")
        return jsonify({"code": 500, "msg": f"创建任务失败: {str(e)}", "data": None}), 500


@app.route('/api/creation_task/<int:task_id>/status', methods=['GET'])
def get_creation_task_status(task_id):
    """获取文案生成任务状态和结果"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM creation_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"code": 404, "msg": "任务不存在"}), 404
            
            task = dict(row)
            
            # 解析 prompt_results
            if task.get('prompt_results'):
                try:
                    task['prompt_results'] = json.loads(task['prompt_results'])
                except:
                    pass
            
            return jsonify({"code": 200, "data": task}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500


@app.route('/api/generate_video', methods=['POST'])
def generate_video():
    """
    AI 视频生成接口
    输入: prompt (视频提示词), provider (可选，默认mock)
    输出: task_id, status, video_url, local_path
    """
    data = request.get_json()
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({
            "code": 400,
            "msg": "缺少 prompt 参数",
            "data": None
        }), 400
    
    provider = data.get('provider', 'mock')
    api_key = data.get('api_key') or os.getenv('VIDEO_API_KEY')
    mock_video_url = data.get('mockVideoUrl', '')  # 从前端获取 Mock URL
    
    # 设置输出目录
    output_dir = str(Path(RUNTIME_DIR / "data/videos"))
    
    try:
        client = get_video_client(
            provider=provider,
            api_key=api_key,
            output_dir=output_dir,
            mock_video_url=mock_video_url if provider == 'mock' else None
        )
        
        result = client.generate_video(prompt)
        
        # 如果是 mock 模式且立即完成，尝试下载（mock 模式下跳过）
        if result.get("_mock"):
            # Mock 模式下模拟完成状态
            result["status"] = "completed"
            result["message"] = "这是模拟模式，实际使用请配置 VIDEO_API_KEY 并选择 provider"
        
        return jsonify({
            "code": 200,
            "msg": "视频生成任务已提交",
            "data": result
        }), 200
        
    except VideoGenerationError as e:
        print(f"视频生成失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"视频生成失败: {str(e)}",
            "data": None
        }), 500
    except Exception as e:
        print(f"视频生成异常: {e}")
        return jsonify({
            "code": 500,
            "msg": f"视频生成异常: {str(e)}",
            "data": None
        }), 500


@app.route('/api/video_status', methods=['GET'])
def video_status():
    """
    查询视频生成状态
    输入: task_id, provider
    """
    task_id = request.args.get('task_id')
    provider = request.args.get('provider', 'mock')
    api_key = request.args.get('api_key') or os.getenv('VIDEO_API_KEY')
    
    if not task_id:
        return jsonify({
            "code": 400,
            "msg": "缺少 task_id 参数",
            "data": None
        }), 400
    
    try:
        client = get_video_client(provider=provider, api_key=api_key)
        result = client.check_status(task_id)
        
        return jsonify({
            "code": 200,
            "msg": "查询成功",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"状态查询失败: {str(e)}",
            "data": None
        }), 500


@app.route('/api/ai_workflow', methods=['POST'])
def ai_workflow():
    """
    完整 AI 工作流接口
    输入: topic, platform, style, llm_config, video_config
    流程: 生成 Prompt -> 生成视频 -> (可选)自动发布
    """
    import json as json_lib
    data = request.get_json()
    topic = data.get('topic')
    
    if not topic:
        return jsonify({
            "code": 400,
            "msg": "缺少 topic 参数",
            "data": None
        }), 400
    
    platform = data.get('platform', 'douyin')
    style = data.get('style', '产品展示')
    auto_publish = data.get('auto_publish', False)
    
    # LLM 配置
    llm_config = data.get('llm_config', {})
    base_url = llm_config.get('base_url') or os.getenv('LLM_BASE_URL')
    api_key = llm_config.get('api_key') or os.getenv('LLM_API_KEY')
    model = llm_config.get('model', 'gpt-4o')
    
    # 视频配置
    video_config = data.get('video_config', {})
    video_provider = video_config.get('provider', 'mock')
    # 根据不同provider获取对应的API key
    if video_provider == 'doubao':
        video_api_key = video_config.get('doubaoApiKey', '') or os.getenv('DOUBAO_API_KEY')
    elif video_provider == 'sora':
        video_api_key = video_config.get('soraApiKey', '') or os.getenv('SORA_API_KEY')
    elif video_provider == 'wanxiang':
        video_api_key = video_config.get('videoApiKey', '') or os.getenv('DASHSCOPE_API_KEY')
    else:
        video_api_key = video_config.get('api_key') or os.getenv('VIDEO_API_KEY')
    
    results = {
        "stage": "prompt",
        "prompt_result": None,
        "video_result": None,
        "publish_result": None
    }
    
    try:
        # Step 1: 生成 Prompt
        if not base_url or not api_key:
            return jsonify({
                "code": 400,
                "msg": "缺少 LLM 配置",
                "data": None
            }), 400
        
        llm_client = LLMClient(base_url=base_url, api_key=api_key, model=model)
        prompt_result = generate_video_prompt(llm_client, topic, platform, style)
        results["prompt_result"] = prompt_result
        results["stage"] = "video"
        
        # Step 2: 生成视频
        output_dir = str(Path(RUNTIME_DIR / "data/videos"))
        # 获取 Mock URL（如果是 mock 模式）
        mock_video_url = video_config.get('mockVideoUrl', '')
        # 获取模型参数
        video_model = None
        if video_provider == 'sora':
            video_model = video_config.get('soraModel', 'sora-2')
        elif video_provider == 'doubao':
            video_model = video_config.get('doubaoModel', 'doubao-seedance-1-5-pro-251215')
        elif video_provider == 'wanxiang':
            video_model = video_config.get('wanxiangModel', 'wan2.6-t2v')
        
        video_client = get_video_client(
            provider=video_provider,
            api_key=video_api_key,
            output_dir=output_dir,
            mock_video_url=mock_video_url if video_provider == 'mock' else None,
            model=video_model if video_model else None
        )
        
        video_prompt = prompt_result.get('video_prompt', topic)
        video_result = video_client.generate_video(video_prompt)
        results["video_result"] = video_result
        
        # 保存到数据库
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO creation_tasks (topic, prompt, title, description, tags, video_task_id, status, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                topic,
                video_prompt,
                prompt_result.get('title', topic),
                prompt_result.get('description', ''),
                json_lib.dumps(prompt_result.get('tags', [])),
                video_result.get('task_id'),
                'generating' if not video_result.get('_mock') else 'completed',
                video_provider
            ))
            conn.commit()
            task_db_id = cursor.lastrowid
        
        results["task_db_id"] = task_db_id
        results["stage"] = "completed"
        
        return jsonify({
            "code": 200,
            "msg": "AI 工作流执行成功",
            "data": results
        }), 200
        
    except Exception as e:
        print(f"AI 工作流失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"AI 工作流失败 (阶段: {results['stage']}): {str(e)}",
            "data": results
        }), 500



# ============== AI 获客任务完整流程 API ==============

@app.route('/api/ai_task/create', methods=['POST'])
def create_ai_task():
    """
    创建 AI 获客任务 (完整流程)
    输入: 
      - prompt_data: {title, description, tags, video_prompt} (已生成的文案数据)
      - account_id: 发布账号ID (可选)
      - auto_publish: 是否自动发布 (默认 false)
      - video_config: {provider, api_key, resolution, duration} 视频生成配置
      - platform: 目标平台 (douyin/xhs/ks/wx)
    流程: 保存任务 -> 调用视频生成 -> (视频完成后)自动发布
    """
    import json as json_lib
    data = request.get_json()
    
    # 获取原始主题 (新增: 从请求中获取原始topic,避免被title覆盖)
    topic = data.get('topic')
    
    prompt_data = data.get('prompt_data', {})
    if not prompt_data.get('video_prompt'):
        return jsonify({
            "code": 400,
            "msg": "缺少视频提示词 (video_prompt)",
            "data": None
        }), 400
    
    account_id = data.get('account_id')
    auto_publish = data.get('auto_publish', False)
    platform = data.get('platform', 'douyin')
    
    # 平台映射 (字符串 -> 数字)
    platform_map = {
        'douyin': 3,
        'xhs': 1,
        'ks': 4,
        'wx': 2,
        'bilibili': 5
    }
    platform_num = platform_map.get(platform, 3)
    
    # 平台名称映射 (为文件命名使用)
    platform_name_map = {
        'douyin': '抖音',
        'xhs': '小红书',
        'ks': '快手',
        'wx': '视频号',
        'bilibili': 'B站'
    }
    platform_display_name = platform_name_map.get(platform, '抖音')
    
    # 视频配置
    video_config = data.get('video_config', {})
    video_provider = video_config.get('provider', 'mock')
    # 根据不同provider获取对应的API key
    if video_provider == 'doubao':
        video_api_key = video_config.get('doubaoApiKey', '') or os.getenv('DOUBAO_API_KEY')
    elif video_provider == 'sora':
        video_api_key = video_config.get('soraApiKey', '') or os.getenv('SORA_API_KEY')
    elif video_provider == 'wanxiang':
        video_api_key = video_config.get('videoApiKey', '') or os.getenv('DASHSCOPE_API_KEY')
    else:
        video_api_key = video_config.get('api_key') or os.getenv('VIDEO_API_KEY')
    video_resolution = video_config.get('resolution', '720p')
    video_duration = video_config.get('duration', 5)
    
    try:
        # Step 1: 保存任务到数据库 (状态: pending)
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # 先确保表有新字段 (简单的迁移)
            try:
                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN account_id INTEGER")
            except sqlite3.OperationalError:
                pass  # 字段已存在
            try:
                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN platform INTEGER DEFAULT 3")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN auto_publish INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            
            cursor.execute('''
                INSERT INTO creation_tasks (
                    topic, prompt, title, description, tags, 
                    status, provider, account_id, platform, auto_publish, platform_str
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                topic or prompt_data.get('title', ''),  # 优先使用原始topic,如未提供则降级使用title
                prompt_data.get('video_prompt', ''),
                prompt_data.get('title', ''),
                prompt_data.get('description', ''),
                json_lib.dumps(prompt_data.get('tags', []), ensure_ascii=False),
                'pending',
                video_provider,
                account_id,
                platform_num,
                1 if auto_publish else 0,
                platform  # 保存平台字符串，用于视频命名
            ))
            conn.commit()
            task_id = cursor.lastrowid
        
        print(f"✅ AI获客任务已创建: ID={task_id}")
        
        # Step 2: 启动异步视频生成
        def generate_and_publish():
            try:
                # 更新状态为 generating
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE creation_tasks SET status = ? WHERE id = ?', 
                        ('generating', task_id)
                    )
                    conn.commit()
                
                # 获取视频客户端
                output_dir = str(Path(RUNTIME_DIR / "data/videos"))
                # 获取 Mock URL（如果是 mock 模式）
                mock_video_url = video_config.get('mockVideoUrl', '')
                client = get_video_client(
                    provider=video_provider,
                    api_key=video_api_key,
                    output_dir=output_dir,
                    resolution=video_resolution,
                    duration=video_duration,
                    mock_video_url=mock_video_url if video_provider == 'mock' else None
                )
                
                # 生成视频
                video_prompt = prompt_data.get('video_prompt', '')
                # 获取模型参数
                video_model = None
                if video_provider == 'sora':
                    video_model = video_config.get('soraModel', 'sora-2')
                elif video_provider == 'doubao':
                    video_model = video_config.get('doubaoModel', 'doubao-seedance-1-5-pro-251215')
                elif video_provider == 'wanxiang':
                    video_model = video_config.get('wanxiangModel', 'wan2.6-t2v')
                result = client.generate_video(video_prompt, model=video_model) if video_model else client.generate_video(video_prompt)
                
                video_task_id = result.get('task_id')
                
                # 保存视频任务ID
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE creation_tasks SET video_task_id = ? WHERE id = ?', 
                        (video_task_id, task_id)
                    )
                    conn.commit()
                
                # 如果是 mock 模式，直接完成
                if result.get('_mock') or video_provider == 'mock':
                    with sqlite3.connect(DATABASE_PATH) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE creation_tasks SET status = ?, video_url = ? WHERE id = ?', 
                            ('completed', 'mock://sample_video.mp4', task_id)
                        )
                        conn.commit()
                    print(f"✅ [Mock] 视频生成完成: task_id={task_id}")
                    
                    # Mock 模式下模拟自动发布
                    if auto_publish and account_id:
                        trigger_auto_publish(task_id)
                    return
                
                # 非 Mock 模式：轮询等待视频完成
                if hasattr(client, 'wait_for_completion'):
                    try:
                        final_result = client.wait_for_completion(video_task_id)
                        video_url = final_result.get('video_url')
                        
                        # 下载视频到本地
                        local_path = None
                        if video_url:
                            try:
                                # 使用主题名称和平台生成文件名（格式：主题_平台-AI.mp4）
                                topic_name = topic or f'task_{task_id}'
                                display_filename = f"{topic_name}_{platform_display_name}-AI.mp4"
                                temp_filename = f"{display_filename}.mp4"
                                
                                local_path = client.download_video(
                                    video_url, 
                                    temp_filename
                                )
                                
                                # 将视频添加到素材库（使用UUID格式，与手动上传一致）
                                if local_path:
                                    import uuid as uuid_lib
                                    video_uuid = str(uuid_lib.uuid1())
                                    uuid_filename = f"{video_uuid}_{topic_name}_{platform_display_name}-AI.mp4"
                                    
                                    # 重命名文件为UUID格式
                                    video_path = Path(local_path)
                                    new_video_path = video_path.parent / uuid_filename
                                    if video_path.exists():
                                        video_path.rename(new_video_path)
                                        local_path = str(new_video_path)
                                    
                                    file_size_mb = round(new_video_path.stat().st_size / (1024 * 1024), 2) if new_video_path.exists() else 0
                                    
                                    with sqlite3.connect(DATABASE_PATH) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            INSERT INTO file_records (filename, filesize, file_path)
                                            VALUES (?, ?, ?)
                                        ''', (display_filename, file_size_mb, uuid_filename))
                                        conn.commit()
                                    
                                    print(f"📦 视频已添加到素材库: {uuid_filename} ({file_size_mb}MB)")
                                    print(f"   前端显示名称: {display_filename}")
                                    
                            except Exception as e:
                                print(f"⚠️ 视频下载失败: {e}")
                        
                        # 更新任务状态
                        with sqlite3.connect(DATABASE_PATH) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE creation_tasks 
                                SET status = ?, video_url = ?, local_video_path = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', ('completed', video_url, local_path, task_id))
                            conn.commit()
                        
                        print(f"✅ 视频生成完成: task_id={task_id}, url={video_url}")
                        
                        # 调试：检查自动发布条件
                        print(f"🔍 检查自动发布条件:")
                        print(f"   - auto_publish: {auto_publish}")
                        print(f"   - account_id: {account_id}")
                        print(f"   - local_path: {local_path}")
                        
                        # 触发自动发布
                        if auto_publish and account_id and local_path:
                            print(f"🚀 满足自动发布条件，准备发布...")
                            trigger_auto_publish(task_id)
                        else:
                            print(f"⚠️ 不满足自动发布条件，跳过自动发布")
                            
                    except VideoGenerationError as e:
                        error_msg = str(e)
                        with sqlite3.connect(DATABASE_PATH) as conn:
                            cursor = conn.cursor()
                            # 确保表有 error_message 字段
                            try:
                                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN error_message TEXT")
                            except sqlite3.OperationalError:
                                pass
                            cursor.execute(
                                'UPDATE creation_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                                ('video_failed', error_msg, task_id)
                            )
                            conn.commit()
                        print(f"❌ 视频生成失败: {error_msg}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ AI任务执行失败: {error_msg}")
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    try:
                        cursor.execute("ALTER TABLE creation_tasks ADD COLUMN error_message TEXT")
                    except sqlite3.OperationalError:
                        pass
                    cursor.execute(
                        'UPDATE creation_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                        ('failed', error_msg, task_id)
                    )
                    conn.commit()
        
        # 在后台线程执行
        threading.Thread(target=generate_and_publish, daemon=True).start()
        
        return jsonify({
            "code": 200,
            "msg": "AI获客任务已创建",
            "data": {
                "task_id": task_id,
                "status": "pending"
            }
        }), 200
        
    except Exception as e:
        print(f"创建AI任务失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"创建任务失败: {str(e)}",
            "data": None
        }), 500


def trigger_auto_publish(task_id: int):
    """触发自动发布流程"""
    from utils.global_state import is_account_locked, acquire_account_lock, release_account_lock
    
    account_id = None  # 用于finally中释放锁
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 确保表有发布状态字段
            try:
                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN publish_status TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE creation_tasks ADD COLUMN publish_error TEXT")
            except sqlite3.OperationalError:
                pass
            
            cursor.execute('SELECT * FROM creation_tasks WHERE id = ?', (task_id,))
            task = cursor.fetchone()
            
            if not task:
                print(f"❌ 任务不存在: {task_id}")
                return
            
            task = dict(task)
            account_id = task.get('account_id')
            local_path = task.get('local_video_path')
            
            if not account_id or not local_path:
                print(f"⚠️ 缺少账号或视频路径，跳过发布: task_id={task_id}")
                return
            
            # 检查账号是否被占用
            lock_info = is_account_locked(account_id)
            if lock_info:
                error_msg = f"账号正在被其他任务占用: {lock_info.get('task_type')}"
                print(f"❌ {error_msg} (账号ID: {account_id})")
                cursor.execute(
                    'UPDATE creation_tasks SET publish_status = ?, publish_error = ? WHERE id = ?',
                    ('publish_failed', error_msg, task_id)
                )
                conn.commit()
                return
            
            # 获取账号锁
            if not acquire_account_lock(account_id, 'ai_publish', f'ai_{task_id}'):
                error_msg = "无法获取账号锁，请稍后重试"
                print(f"❌ {error_msg} (账号ID: {account_id})")
                return
            
            # 获取账号 cookie 路径和平台类型
            cursor.execute('SELECT filePath, type FROM user_info WHERE id = ?', (account_id,))
            acc_row = cursor.fetchone()
            if not acc_row:
                print(f"❌ 账号不存在: {account_id}")
                return
            
            cookie_path = acc_row['filePath']
            platform = acc_row['type']  # 从账号表获取真实平台类型
            
            # 【任务前验证】检查cookie状态(使用缓存)
            current_time = time.time()
            last_check = CHECK_CACHE.get(account_id, 0)
            
            if current_time - last_check > CACHE_DURATION:
                # 缓存过期,重新验证
                print(f"🔍 验证账号 {account_id} 的cookie状态...")
                
                import asyncio
                try:
                    # 传递完整路径，而非仅文件名
                    is_valid = asyncio.run(check_cookie(platform, cookie_path))
                except Exception as e:
                    print(f"⚠️ Cookie验证出错: {e}")
                    is_valid = False
                
                CHECK_CACHE[account_id] = current_time
                
                if not is_valid:
                    # 更新数据库账号状态为失效
                    cursor.execute('UPDATE user_info SET status = 0 WHERE id = ?', (account_id,))
                    conn.commit()
                    
                    error_msg = "账号cookie已失效,请在账号管理中同步状态或重新登录"
                    cursor.execute(
                        'UPDATE creation_tasks SET publish_status = ?, publish_error = ? WHERE id = ?',
                        ('publish_failed', error_msg, task_id)
                    )
                    conn.commit()
                    print(f"❌ {error_msg} (账号ID: {account_id})")
                    return
                else:
                    print(f"✅ 账号 {account_id} cookie有效")
            else:
                remaining = int(CACHE_DURATION - (current_time - last_check))
                print(f"📦 使用缓存: 账号 {account_id} cookie状态, 剩余有效期 {remaining}秒")
            
            # 解析标签
            tags = []
            try:
                tags = json.loads(task.get('tags', '[]'))
            except:
                pass
            
            # 更新状态为发布中
            cursor.execute(
                'UPDATE creation_tasks SET publish_status = ? WHERE id = ?',
                ('publishing', task_id)
            )
            conn.commit()
            
            print(f"🚀 触发自动发布: task_id={task_id}, platform={platform}, account={account_id}")
            
            # 直接使用数据库中存储的 profile_dir 路径
            profile_dir = cookie_path  # cookie_path 现在存储的是 profile_dir 路径
            video_filename = Path(local_path).name
            
            # 根据平台调用对应的发布函数
            if platform == 3:  # 抖音
                post_video_DouYin_with_taskid(
                    title=task.get('title', ''),
                    files=[video_filename],
                    tags=tags,
                    profile_dirs=[profile_dir],
                    category=None,
                    enableTimer=False,
                    videos_per_day=1,
                    daily_times=[],
                    start_days=0,
                    thumbnail_path='',
                    description=task.get('description', ''),
                    task_id=f"ai_{task_id}"
                )
            elif platform == 1:  # 小红书
                post_video_xhs(
                    title=task.get('title', ''),
                    files=[video_filename],
                    tags=tags,
                    profile_dirs=[profile_dir],
                    category=None,
                    enableTimer=False,
                    videos_per_day=1,
                    daily_times=[],
                    start_days=0,
                    description=task.get('description', ''),
                    task_id=f"ai_{task_id}"
                )
            elif platform == 2:  # 视频号
                post_video_tencent(
                    title=task.get('title', ''),
                    files=[video_filename],
                    tags=tags,
                    profile_dirs=[profile_dir],
                    category=None,
                    enableTimer=False,
                    videos_per_day=1,
                    daily_times=[],
                    start_days=0,
                    is_draft=False,
                    task_id=f"ai_{task_id}",
                    description=task.get('description', '')
                )
            elif platform == 4:  # 快手
                post_video_ks(
                    title=task.get('title', ''),
                    files=[video_filename],
                    tags=tags,
                    profile_dirs=[profile_dir],
                    category=None,
                    enableTimer=False,
                    videos_per_day=1,
                    daily_times=[],
                    start_days=0,
                    description=task.get('description', ''),
                    task_id=f"ai_{task_id}"
                )
            elif platform == 5:  # B站
                post_video_bilibili(
                    title=task.get('title', ''),
                    files=[video_filename],
                    tags=tags,
                    profile_dirs=[profile_dir],
                    category=None,
                    enableTimer=False,
                    videos_per_day=1,
                    daily_times=[],
                    start_days=0,
                    description=task.get('description', ''),
                    task_id=f"ai_{task_id}"
                )
            
            # 发布成功，更新状态
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE creation_tasks SET status = ?, publish_status = ?, publish_error = NULL WHERE id = ?',
                    ('published', 'published', task_id)
                )
                conn.commit()
            print(f"✅ 自动发布完成: task_id={task_id}")
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 自动发布失败: {error_msg}")
        # 更新状态为发布失败
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE creation_tasks SET publish_status = ?, publish_error = ? WHERE id = ?',
                    ('publish_failed', error_msg, task_id)
                )
                conn.commit()
        except Exception as db_err:
            print(f"❌ 更新失败状态错误: {db_err}")
    finally:
        # 确保释放账号锁
        if account_id:
            release_account_lock(account_id)
            print(f"🔓 已释放账号锁: {account_id}")


@app.route('/api/ai_task/<int:task_id>/status', methods=['GET'])
def get_ai_task_status(task_id):
    """获取AI任务状态"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM creation_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"code": 404, "msg": "任务不存在"}), 404
            
            return jsonify({
                "code": 200,
                "data": dict(row)
            }), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500


# ============== 任务管理 API ==============

# AI 获客任务管理 (creation_tasks 表)
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有 AI 获客任务列表"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM creation_tasks ORDER BY created_at DESC
            ''')
            rows = cursor.fetchall()
            tasks = [dict(row) for row in rows]
            return jsonify({
                "code": 200,
                "msg": "获取成功",
                "data": tasks
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"获取任务列表失败: {str(e)}",
            "data": []
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除 AI 获客任务"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM creation_tasks WHERE id = ?', (task_id,))
            conn.commit()
            
            return jsonify({
                "code": 200,
                "msg": "任务删除成功",
                "data": None
            }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"删除任务失败: {str(e)}",
            "data": None
        }), 500

# 发布任务管理 (publish_tasks 表)
@app.route('/api/publish_tasks', methods=['GET'])
def get_publish_tasks():
    """获取所有发布任务（统一表）"""
    task_type = request.args.get('type') # 'manual' or 'ai'
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM publish_tasks"
            params = []
            if task_type:
                query += " WHERE task_type = ?"
                params.append(task_type)
            query += " ORDER BY created_at DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return jsonify({"code": 200, "data": [dict(row) for row in rows]}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/api/publish_tasks/<int:task_id>', methods=['DELETE'])
def delete_publish_task(task_id):
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM publish_tasks WHERE id = ?', (task_id,))
            conn.commit()
            return jsonify({"code": 200, "msg": "删除成功"}), 200
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)}), 500

@app.route('/api/publish_tasks/<int:task_id>/status')
def publish_task_status(task_id):
    def generate():
        while True:
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT status, progress, error_message FROM publish_tasks WHERE id = ?', (task_id,))
                row = cursor.fetchone()
                if row:
                    data = json.dumps(dict(row))
                    yield f"data: {data}\n\n"
                    if row['status'] in ['completed', 'failed']:
                        break
                else:
                    break
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')

# SSE 流生成器函数
def sse_stream(status_queue):
    while True:
        if not status_queue.empty():
            msg = status_queue.get()
            yield f"data: {msg}\n\n"
        else:
            # 避免 CPU 占满
            time.sleep(0.1)


# ============== 远程账号添加接口 ==============
# 用于接收登录客户端上传的加密Cookie

@app.route('/api/addAccountRemote', methods=['POST'])
def add_account_remote():
    """
    接收远程登录客户端上传的加密Cookie
    
    请求体:
    {
        "platform": 3,  // 1=小红书, 2=视频号, 3=抖音, 4=快手
        "userName": "账号名称",
        "encryptedCookie": "加密的Cookie数据"
    }
    """
    try:
        data = request.get_json()
        platform = data.get('platform')
        user_name = data.get('userName')
        encrypted_cookie = data.get('encryptedCookie')
        
        # 参数验证
        if not all([platform, user_name, encrypted_cookie]):
            return jsonify({
                "code": 400,
                "msg": "缺少必要参数 (platform, userName, encryptedCookie)",
                "data": None
            }), 400
        
        if platform not in [1, 2, 3, 4]:
            return jsonify({
                "code": 400,
                "msg": "无效的平台类型",
                "data": None
            }), 400
        
        # 解密Cookie
        try:
            from utils.crypto_utils import decrypt_cookie
            cookie_data = decrypt_cookie(encrypted_cookie)
        except Exception as e:
            print(f"Cookie解密失败: {e}")
            return jsonify({
                "code": 400,
                "msg": f"Cookie解密失败: {e}",
                "data": None
            }), 400
        
        # 生成Cookie文件名
        cookie_uuid = uuid.uuid1()
        cookie_filename = f"{cookie_uuid}.json"
        cookie_path = Path(BASE_DIR / "data/cookies" / cookie_filename)
        
        # 确保目录存在
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存Cookie文件
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Cookie文件已保存: {cookie_filename}")
        
        # 验证Cookie有效性（异步）
        async def verify_and_save():
            from rpa_service.auth import check_cookie
            is_valid = await check_cookie(platform, cookie_filename)
            
            status = 1 if is_valid else 0
            
            # 保存到数据库
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_info (type, filePath, userName, status)
                    VALUES (?, ?, ?, ?)
                ''', (platform, cookie_filename, user_name, status))
                conn.commit()
                account_id = cursor.lastrowid
            
            print(f"✅ 账号已添加 (ID={account_id}, 状态={status})")
            return account_id, status
        
        # 在新线程中执行验证
        import asyncio
        
        def run_verify():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(verify_and_save())
        
        # 先同步保存到数据库（状态为待验证）
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_info (type, filePath, userName, status)
                VALUES (?, ?, ?, ?)
            ''', (platform, cookie_filename, user_name, 1))  # 默认有效
            conn.commit()
            account_id = cursor.lastrowid
        
        print(f"✅ 远程账号添加成功 (ID={account_id})")
        
        return jsonify({
            "code": 200,
            "msg": "账号添加成功",
            "data": {"accountId": account_id}
        }), 200
    
    except Exception as e:
        print(f"远程添加账号失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"添加失败: {str(e)}",
            "data": None
        }), 500





if __name__ == '__main__':
    import webbrowser
    import sys
    from io import StringIO
    from queue import Queue
    
    PORT = 5409
    URL = f'http://localhost:{PORT}'
    
    # 初始化 Cookie 定时验证调度器
    init_scheduler(app)
    # 注册退出时关闭调度器
    atexit.register(shutdown_scheduler)
    
    # 检测是否为 PyInstaller 打包环境
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # 日志队列，用于在 GUI 中显示
        log_queue = Queue()
        
        # 使用日志处理器捕获日志，而不是重定向 stdout
        import logging
        
        class QueueHandler(logging.Handler):
            """将日志发送到队列的处理器"""
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.queue.put(msg)
                except Exception:
                    pass
        
        # 添加队列处理器到根日志记录器
        queue_handler = QueueHandler(log_queue)
        queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        logging.getLogger().addHandler(queue_handler)
        
        def run_gui():
            """运行 CustomTkinter GUI 控制面板"""
            import customtkinter as ctk
            from tkinter import messagebox
            
            # 设置主题
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            
            # 创建主窗口
            app_window = ctk.CTk()
            app_window.title("PostBridge")
            app_window.geometry("500x200")
            app_window.resizable(True, True)
            app_window.minsize(500, 200)
            
            # 状态变量
            log_visible = False
            
            # ============ 顶部状态区域 ============
            header_frame = ctk.CTkFrame(app_window, fg_color="#1a7f37", corner_radius=0)
            header_frame.pack(fill="x", padx=0, pady=0)
            
            status_label = ctk.CTkLabel(
                header_frame,
                text="Running",
                font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
                text_color="white"
            )
            status_label.pack(pady=15)
            
            # ============ 信息区域 ============
            info_frame = ctk.CTkFrame(app_window, fg_color="transparent")
            info_frame.pack(fill="x", padx=20, pady=(15, 5))
            
            url_label = ctk.CTkLabel(
                info_frame,
                text=f"URL: {URL}",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=("#333", "#ddd")
            )
            url_label.pack(side="left")
            
            # 复制按钮
            def copy_url():
                app_window.clipboard_clear()
                app_window.clipboard_append(URL)
                messagebox.showinfo("Copied", f"Copied to clipboard:\n{URL}")
            
            copy_btn = ctk.CTkButton(
                info_frame,
                text="Copy",
                width=50,
                height=25,
                font=ctk.CTkFont(size=12),
                fg_color="#6c757d",
                hover_color="#5a6268",
                command=copy_url
            )
            copy_btn.pack(side="left", padx=10)
            
            # ============ 按钮区域 ============
            btn_frame = ctk.CTkFrame(app_window, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=15)
            
            def open_browser():
                webbrowser.open(URL)
            
            def toggle_log():
                nonlocal log_visible
                if log_visible:
                    log_frame.pack_forget()
                    log_btn.configure(text="Show logs")
                    app_window.geometry("500x200")
                    log_visible = False
                else:
                    log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
                    log_btn.configure(text="Hide logs")
                    app_window.geometry("600x500")
                    log_visible = True
            
            def exit_app():
                if messagebox.askokcancel("Exit", "Closing this window will stop the service. Exit now?"):
                    app_window.destroy()
                    os._exit(0)
            
            # 打开浏览器按钮
            browser_btn = ctk.CTkButton(
                btn_frame,
                text="Open browser",
                font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
                fg_color="#0d6efd",
                hover_color="#0b5ed7",
                height=40,
                corner_radius=8,
                command=open_browser
            )
            browser_btn.pack(side="left", padx=(0, 10))
            
            # 查看日志按钮
            log_btn = ctk.CTkButton(
                btn_frame,
                text="Show logs",
                font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
                fg_color="#fd7e14",
                hover_color="#e96b02",
                height=40,
                corner_radius=8,
                command=toggle_log
            )
            log_btn.pack(side="left", padx=(0, 10))
            
            # 退出按钮
            exit_btn = ctk.CTkButton(
                btn_frame,
                text="Stop service",
                font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
                fg_color="#dc3545",
                hover_color="#bb2d3b",
                height=40,
                corner_radius=8,
                command=exit_app
            )
            exit_btn.pack(side="left")
            
            # ============ 日志区域（默认隐藏） ============
            log_frame = ctk.CTkFrame(app_window, fg_color="transparent")
            
            log_title = ctk.CTkLabel(
                log_frame,
                text="Console output",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=("#666", "#aaa"),
                anchor="w"
            )
            log_title.pack(fill="x", pady=(0, 5))
            
            log_textbox = ctk.CTkTextbox(
                log_frame,
                font=ctk.CTkFont(family="Consolas", size=11),
                fg_color="#1e1e1e",
                text_color="#d4d4d4",
                corner_radius=8,
                wrap="word"
            )
            log_textbox.pack(fill="both", expand=True)
            log_textbox.configure(state="disabled")
            
            # 定时更新日志
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            
            def strip_ansi(text):
                """移除 ANSI 颜色代码"""
                return ansi_escape.sub('', text)
            
            def update_log():
                while not log_queue.empty():
                    try:
                        msg = log_queue.get_nowait()
                        # 移除 ANSI 颜色代码
                        clean_msg = strip_ansi(msg)
                        log_textbox.configure(state="normal")
                        log_textbox.insert("end", clean_msg + "\n")
                        log_textbox.see("end")
                        log_textbox.configure(state="disabled")
                    except:
                        break
                app_window.after(100, update_log)
            
            update_log()
            
            # 关闭窗口时的处理
            app_window.protocol("WM_DELETE_WINDOW", exit_app)
            
            # 自动打开浏览器
            app_window.after(800, open_browser)
            
            # 添加初始日志
            log_queue.put("PostBridge service started")
            log_queue.put(f"Listening on: {URL}")
            log_queue.put("=" * 50)
            
            # 运行主循环
            app_window.mainloop()
        
        # 在新线程中运行 GUI
        gui_thread = threading.Thread(target=run_gui, daemon=True)
        gui_thread.start()
        
    else:
        # 开发环境：只打印信息
        print(f"Service started: {URL}")
    
    # 使用 Waitress 生产服务器启动 Flask（消除开发服务器警告）
    from waitress import serve
    import logging
    
    # 配置 Waitress 访问日志
    waitress_logger = logging.getLogger('waitress')
    waitress_logger.setLevel(logging.INFO)
    
    # 添加请求日志中间件
    from paste.translogger import TransLogger
    app_with_logging = TransLogger(app, setup_console_handler=True)
    
    print(f"Waitress server starting: http://0.0.0.0:{PORT}")
    print("Detailed request logging enabled")
    serve(app_with_logging, host='0.0.0.0', port=PORT, threads=4)
