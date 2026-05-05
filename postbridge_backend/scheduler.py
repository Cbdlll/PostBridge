# -*- coding: utf-8 -*-
"""
Cookie 定时验证调度器
每 24 小时自动验证所有账号的 Cookie 有效性
"""
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from conf import DATABASE_PATH
from rpa_service.auth import check_cookie

# 全局调度器实例
_scheduler: Optional[BackgroundScheduler] = None

# 验证间隔（秒）
VALIDATION_INTERVAL_SECONDS = 24 * 60 * 60  # 24小时


def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DATABASE_PATH)


def validate_all_cookies():
    """
    验证所有账号的 Cookie 有效性
    更新数据库状态和 last_validated_at 时间戳
    """
    print(f"\n🔄 [Scheduler] 开始定时 Cookie 验证任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, type, filePath, userName FROM user_info')
            accounts = cursor.fetchall()
            
            if not accounts:
                print("📋 [Scheduler] 无账号需要验证")
                return
            
            print(f"📋 [Scheduler] 共 {len(accounts)} 个账号待验证")
            
            valid_count = 0
            invalid_count = 0
            
            for account in accounts:
                account_id, platform_type, file_path, user_name = account
                
                try:
                    # 执行异步验证
                    is_valid = asyncio.run(check_cookie(platform_type, file_path))
                    
                    # 更新数据库状态和验证时间
                    new_status = 1 if is_valid else 0
                    cursor.execute('''
                        UPDATE user_info 
                        SET status = ?, last_validated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (new_status, account_id))
                    
                    if is_valid:
                        valid_count += 1
                        print(f"  ✅ [{user_name}] Cookie 有效")
                    else:
                        invalid_count += 1
                        print(f"  ❌ [{user_name}] Cookie 已失效")
                        
                except Exception as e:
                    invalid_count += 1
                    print(f"  ⚠️ [{user_name}] 验证出错: {e}")
                    # 验证出错视为失效
                    cursor.execute('''
                        UPDATE user_info 
                        SET status = 0, last_validated_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (account_id,))
            
            conn.commit()
            print(f"\n📊 [Scheduler] 验证完成: {valid_count} 有效, {invalid_count} 失效")
            
    except Exception as e:
        print(f"❌ [Scheduler] 定时验证任务执行失败: {e}")


def init_scheduler(app=None):
    """
    初始化并启动定时任务调度器
    
    Args:
        app: Flask 应用实例（可选，用于上下文绑定）
    """
    global _scheduler
    
    if _scheduler is not None:
        print("⚠️ [Scheduler] 调度器已初始化，跳过")
        return _scheduler
    
    _scheduler = BackgroundScheduler(
        timezone='Asia/Shanghai',
        job_defaults={
            'coalesce': True,  # 合并错过的任务
            'max_instances': 1  # 同一任务最多一个实例
        }
    )
    
    # 添加定时验证任务
    _scheduler.add_job(
        func=validate_all_cookies,
        trigger=IntervalTrigger(seconds=VALIDATION_INTERVAL_SECONDS),
        id='cookie_validation_job',
        name='Cookie 定时验证',
        replace_existing=True
    )
    
    _scheduler.start()
    print(f"🚀 [Scheduler] Cookie 定时验证任务已启动 (间隔: {VALIDATION_INTERVAL_SECONDS // 3600} 小时)")
    
    return _scheduler


def shutdown_scheduler():
    """关闭调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        print("🛑 [Scheduler] 调度器已关闭")


def trigger_validation_now():
    """
    立即触发一次验证（用于手动触发或首次启动）
    """
    print("⚡ [Scheduler] 手动触发 Cookie 验证...")
    validate_all_cookies()


def get_last_validated_time(account_id: int) -> Optional[datetime]:
    """
    从数据库获取账号的上次验证时间
    
    Args:
        account_id: 账号 ID
        
    Returns:
        上次验证时间，若无记录则返回 None
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT last_validated_at FROM user_info WHERE id = ?', 
                (account_id,)
            )
            result = cursor.fetchone()
            
            if result and result[0]:
                return datetime.fromisoformat(result[0])
            return None
    except Exception:
        return None


def is_cache_valid(account_id: int, cache_duration_seconds: int = VALIDATION_INTERVAL_SECONDS) -> bool:
    """
    检查账号的缓存是否仍然有效（基于数据库持久化）
    
    Args:
        account_id: 账号 ID
        cache_duration_seconds: 缓存有效期（秒）
        
    Returns:
        缓存是否有效
    """
    last_validated = get_last_validated_time(account_id)
    
    if last_validated is None:
        return False
    
    elapsed = (datetime.now() - last_validated).total_seconds()
    return elapsed < cache_duration_seconds
