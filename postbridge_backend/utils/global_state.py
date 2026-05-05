# -*- coding: utf-8 -*-
"""
全局状态模块 - 带自动过期清理的队列字典
"""
from queue import Queue
import time


class ExpiringDict:
    """
    自动过期字典，防止长时间运行内存泄漏
    默认30分钟(1800秒)过期
    """
    def __init__(self, ttl=1800):
        self._data = {}
        self._times = {}
        self._ttl = ttl
    
    def __setitem__(self, key, value):
        self._cleanup()
        self._data[key] = value
        self._times[key] = time.time()
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        self._cleanup()
        return key in self._data
    
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]
        if key in self._times:
            del self._times[key]
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def _cleanup(self):
        """清理过期项"""
        now = time.time()
        expired = [k for k, t in list(self._times.items()) if now - t > self._ttl]
        for k in expired:
            if k in self._data:
                del self._data[k]
            if k in self._times:
                del self._times[k]


# 活跃的SSE队列 (30分钟自动过期)
active_queues = ExpiringDict(ttl=1800)

# 验证码队列 (30分钟自动过期)
verification_queues = ExpiringDict(ttl=1800)

# 账号锁状态 (10分钟自动过期，防止锁遗留)
# 格式: {account_id: {"task_type": "ai_publish/manual_browser", "start_time": timestamp, "task_id": str}}
account_locks = ExpiringDict(ttl=600)


def acquire_account_lock(account_id: int, task_type: str, task_id: str = None) -> bool:
    """
    尝试获取账号锁
    
    Args:
        account_id: 账号ID
        task_type: 任务类型 ("ai_publish", "manual_browser", "rpa_publish")
        task_id: 任务ID (可选)
    
    Returns:
        bool: 是否成功获取锁
    """
    if account_id in account_locks:
        return False
    account_locks[account_id] = {
        "task_type": task_type,
        "start_time": time.time(),
        "task_id": task_id
    }
    return True


def release_account_lock(account_id: int) -> bool:
    """
    释放账号锁
    
    Args:
        account_id: 账号ID
    
    Returns:
        bool: 是否成功释放
    """
    if account_id in account_locks:
        del account_locks[account_id]
        return True
    return False


def is_account_locked(account_id: int) -> dict:
    """
    检查账号是否被锁定
    
    Returns:
        dict: 锁信息，如果未锁定返回None
    """
    if account_id in account_locks:
        return account_locks.get(account_id)
    return None


def get_all_locked_accounts() -> dict:
    """获取所有被锁定的账号"""
    return dict(account_locks._data)
