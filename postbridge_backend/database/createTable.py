import sqlite3
import json
import os

# 数据库文件路径（如果不存在会自动创建）
db_file = './database.db'

# 如果数据库已存在，则删除旧的表（可选）
# if os.path.exists(db_file):
#     os.remove(db_file)

# 连接到SQLite数据库（如果文件不存在则会自动创建）
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# 创建账号记录表
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type INTEGER NOT NULL,
    filePath TEXT NOT NULL,  -- 存储文件路径
    userName TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    last_validated_at DATETIME  -- Cookie 上次验证时间（持久化缓存）
)
''')


# 创建文件记录表
cursor.execute('''CREATE TABLE IF NOT EXISTS file_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- 唯一标识每条记录
    filename TEXT NOT NULL,               -- 文件名
    filesize REAL,                     -- 文件大小（单位：MB）
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP, -- 上传时间，默认当前时间
    file_path TEXT                        -- 文件路径
)
''')

# 创建 AI 创作任务表
cursor.execute('''CREATE TABLE IF NOT EXISTS creation_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,                  -- 用户输入的主题
    prompt TEXT,                          -- LLM 生成的视频提示词
    title TEXT,                           -- 生成的视频标题
    description TEXT,                     -- 生成的视频简介
    tags TEXT,                            -- 标签（JSON 数组）
    video_task_id TEXT,                   -- 视频生成任务 ID
    video_url TEXT,                       -- 远程视频 URL
    local_video_path TEXT,                -- 本地视频路径
    status TEXT DEFAULT 'pending',        -- pending/generating/completed/failed
    provider TEXT DEFAULT 'mock',          -- 视频生成服务商
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
# 创建发布任务表（统一管理手动发布和AI获客任务）
cursor.execute('''CREATE TABLE IF NOT EXISTS publish_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,              -- 'manual' | 'ai'
    platform INTEGER NOT NULL,            -- 1:小红书 2:视频号 3:抖音 4:快手
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT,                            -- JSON 数组
    video_path TEXT,                      -- 视频本地路径
    account_ids TEXT,                     -- JSON 数组 (账号 ID 列表)
    status TEXT DEFAULT 'pending',        -- pending/running/completed/failed
    error_message TEXT,                   -- 失败原因
    progress INTEGER DEFAULT 0,           -- 进度百分比
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')



# 提交更改
conn.commit()
print("✅ 表创建成功")
# 关闭连接
conn.close()