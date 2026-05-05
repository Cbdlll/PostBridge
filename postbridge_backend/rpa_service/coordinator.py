import asyncio
import uuid
import atexit
from queue import Queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from conf import BASE_DIR, RUNTIME_DIR
from rpa_service.douyin.main import DouYinVideo
from rpa_service.kuaishou.main import KSVideo
from rpa_service.shipinhao.main import TencentVideo
from rpa_service.xhs.main import XiaoHongShuVideo
from rpa_service.bilibili.main import BilibiliVideo
from utils.constant import TencentZoneTypes
from utils.files_times import generate_schedule_time_next_day

# ========================
# 全局线程池管理
# ========================
# 限制最大并发RPA任务数量，防止资源耗尽
RPA_MAX_WORKERS = 3  # 最多同时运行3个RPA任务
_rpa_executor: ThreadPoolExecutor = None


def get_rpa_executor() -> ThreadPoolExecutor:
    """获取全局RPA线程池（懒加载）"""
    global _rpa_executor
    if _rpa_executor is None:
        _rpa_executor = ThreadPoolExecutor(
            max_workers=RPA_MAX_WORKERS,
            thread_name_prefix="rpa_worker"
        )
        print(f"✅ RPA线程池已初始化: max_workers={RPA_MAX_WORKERS}")
    return _rpa_executor


def shutdown_rpa_executor():
    """关闭RPA线程池（优雅退出）"""
    global _rpa_executor
    if _rpa_executor is not None:
        print("🔄 正在关闭RPA线程池...")
        _rpa_executor.shutdown(wait=False, cancel_futures=True)
        _rpa_executor = None
        print("✅ RPA线程池已关闭")


# 注册退出时清理
atexit.register(shutdown_rpa_executor)


def post_video_tencent(title, files, tags, profile_dirs, category=TencentZoneTypes.LIFESTYLE.value, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0, is_draft=False, task_id=None, description=''):
    """视频号视频发布函数"""
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    for index, file in enumerate(files):
        for profile_dir in profile_dirs:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{description}")
            print(f"Hashtag：{tags}")
            print(f"Profile: {profile_dir}")
            if task_id:
                print(f"任务ID: {task_id}")
            app = TencentVideo(title, str(file), tags, publish_datetimes[index], profile_dir, category, is_draft, task_id, description)
            
            # 与其他平台一致的异步调用方式（处理线程内调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(app.main())
                else:
                    loop.run_until_complete(app.main())
            except RuntimeError:
                asyncio.run(app.main())


def post_video_DouYin(title,files,tags,profile_dirs,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                      thumbnail_path = '',
                      productLink = '', productTitle = ''):
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    # 为该任务创建唯一ID和验证码队列
    task_id = str(uuid.uuid4())
    verification_queue = Queue()
    
    # 注册验证码队列到全局
    from utils.global_state import verification_queues
    verification_queues[task_id] = verification_queue
    
    try:
        for index, file in enumerate(files):
            for profile_dir in profile_dirs:
                print(f"文件路径{str(file)}")
                print(f"视频文件名：{file}")
                print(f"标题：{title}")
                print(f"Hashtag：{tags}")
                print(f"Profile: {profile_dir}")
                print(f"任务ID: {task_id}")
                app = DouYinVideo(title, str(file), tags, publish_datetimes[index], profile_dir, 
                                thumbnail_path, productLink, productTitle, 
                                verification_queue, task_id)
                asyncio.run(app.main(), debug=False)
    finally:
        # 清理验证码队列
        if task_id in verification_queues:
            del verification_queues[task_id]


def post_video_DouYin_with_taskid(title,files,tags,profile_dirs,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                      thumbnail_path = '',
                      description = '', task_id=None):
    """带task_id参数的抖音发布函数，用于从外部传入task_id"""
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    # 使用传入的task_id或创建新的
    if not task_id:
        task_id = str(uuid.uuid4())
    
    verification_queue = Queue()
    
    # 注册验证码队列到全局
    from utils.global_state import verification_queues
    verification_queues[task_id] = verification_queue
    
    try:
        for index, file in enumerate(files):
            for profile_dir in profile_dirs:
                print(f"文件路径{str(file)}")
                print(f"视频文件名：{file}")
                print(f"标题：{title}")
                print(f"简介：{description}")
                print(f"Hashtag：{tags}")
                print(f"Profile: {profile_dir}")
                print(f"任务ID: {task_id}")
                app = DouYinVideo(title, str(file), tags, publish_datetimes[index], profile_dir, 
                                thumbnail_path, description, verification_queue, task_id)
                import asyncio
                # 如果当前有运行中的 loop，直接创建任务；否则创建新 loop（处理线程内调用）
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(app.main())
                    else:
                        loop.run_until_complete(app.main())
                except RuntimeError:
                    asyncio.run(app.main())
    finally:
        # 清理验证码队列
        if task_id in verification_queues:
            del verification_queues[task_id]


def post_video_ks(title,files,tags,profile_dirs,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                  description='', task_id=None):
    """快手视频发布函数"""
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(len(files), videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = [0 for i in range(len(files))]
    
    for index, file in enumerate(files):
        for profile_dir in profile_dirs:
            print(f"文件路径{str(file)}")
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{description}")
            print(f"Hashtag：{tags}")
            print(f"Profile: {profile_dir}")
            if task_id:
                print(f"任务ID: {task_id}")
            app = KSVideo(title, str(file), tags, publish_datetimes[index], profile_dir, description, task_id)
            
            # 与抖音一致的异步调用方式（处理线程内调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(app.main())
                else:
                    loop.run_until_complete(app.main())
            except RuntimeError:
                asyncio.run(app.main())

def post_video_xhs(title,files,tags,profile_dirs,category=TencentZoneTypes.LIFESTYLE.value,enableTimer=False,videos_per_day = 1, daily_times=None,start_days = 0,
                   description='', task_id=None):
    """小红书视频发布函数"""
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times,start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for profile_dir in profile_dirs:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{description}")
            print(f"Hashtag：{tags}")
            print(f"Profile: {profile_dir}")
            if task_id:
                print(f"任务ID: {task_id}")
            app = XiaoHongShuVideo(title, file, tags, publish_datetimes, profile_dir, None, description, task_id)
            
            # 与抖音一致的异步调用方式（处理线程内调用）
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(app.main())
                else:
                    loop.run_until_complete(app.main())
            except RuntimeError:
                asyncio.run(app.main())


# post_video("333",["demo.mp4"],"d","d")
# post_video_DouYin("333",["demo.mp4"],"d","d")

def post_video_bilibili(title, files, tags, profile_dirs, category=TencentZoneTypes.LIFESTYLE.value, enableTimer=False, videos_per_day=1, daily_times=None, start_days=0,
                        description='', task_id=None):
    """Bilibili 视频发布函数"""
    # 生成文件的完整路径，确保只使用文件名（防止相对路径攻击）
    files = [Path(RUNTIME_DIR / "data/videos" / Path(file).name) for file in files]
    file_num = len(files)
    if enableTimer:
        publish_datetimes = generate_schedule_time_next_day(file_num, videos_per_day, daily_times, start_days)
    else:
        publish_datetimes = 0
    for index, file in enumerate(files):
        for profile_dir in profile_dirs:
            print(f"视频文件名：{file}")
            print(f"标题：{title}")
            print(f"简介：{description}")
            print(f"Hashtag：{tags}")
            print(f"Profile: {profile_dir}")
            if task_id:
                print(f"任务ID: {task_id}")
            app = BilibiliVideo(title, str(file), tags, publish_datetimes, profile_dir, description, task_id)
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(app.main())
                else:
                    loop.run_until_complete(app.main())
            except RuntimeError:
                asyncio.run(app.main())