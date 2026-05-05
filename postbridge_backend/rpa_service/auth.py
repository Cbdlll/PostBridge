"""
账号验证模块 - 使用 UserDataDir 持久化浏览器验证登录状态
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger, douyin_logger, bilibili_logger, xiaohongshu_logger

# 平台验证 URL 和登录检测配置
PLATFORM_CONFIG = {
    1: {  # 小红书
        'name': 'xhs',
        'url': 'https://creator.xiaohongshu.com/publish/publish',
        'login_selectors': [],  # 小红书登录后页面也可能有相关文字，改用 URL 检测
        'login_url_pattern': '/login',  # 未登录会重定向到 /login
        'logger': xiaohongshu_logger,
    },
    2: {  # 视频号
        'name': 'shipinhao',
        'url': 'https://channels.weixin.qq.com/platform',  # 使用主页，更稳定
        'login_selectors': [],
        'login_url_pattern': 'login',  # 未登录会重定向到包含 login 的 URL
        'logger': tencent_logger,
    },
    3: {  # 抖音
        'name': 'douyin',
        'url': 'https://creator.douyin.com/creator-micro/content/upload',
        # 登录元素（未登录时出现）
        'login_selectors': ['text=扫码登录', 'text=验证码登录', 'text=密码登录', 'text=抖音APP'],
        # 登录成功元素（已登录时出现）- 基于实际页面结构
        'success_selectors': [
            'text=发布视频',           # 顶部 Tab
            'text=发布图文',           # 顶部 Tab  
            'text=点击上传',           # 上传区域
            'text=上传视频',           # 上传按钮
            'text=内容管理',           # 左侧菜单
            'text=数据中心',           # 左侧菜单
            'text=创作中心',           # 左侧菜单
            '.semi-navigation',       # 左侧导航栏 CSS 类
        ],
        'logger': douyin_logger,
    },
    4: {  # 快手
        'name': 'kuaishou',
        'url': 'https://cp.kuaishou.com/article/publish/video',
        'login_selectors': ['text=立即登录'],
        'login_page_keywords': ['立即登录', '平台优势', '快手创作者服务平台'],  # 登录页特征
        'success_selectors': ['text=上传图文', 'text=上传全景视频', 'text=拖拽视频到此或点击上传'],  # 已登录特征
        'logger': kuaishou_logger,
    },
    5: {  # Bilibili
        'name': 'bilibili',
        'url': 'https://member.bilibili.com/platform/upload/video/frame',
        'login_selectors': [],  # B站通过 URL 跳转检测
        'login_url_pattern': 'passport.bilibili.com',
        'logger': bilibili_logger,
    },
}


async def check_cookie(platform_type: int, profile_dir_path: str) -> bool:
    """
    验证账号登录状态（使用 UserDataDir 持久化浏览器）
    
    Args:
        platform_type: 平台类型 (1=小红书, 2=视频号, 3=抖音, 4=快手, 5=B站)
        profile_dir_path: UserDataDir 路径
    
    Returns:
        bool: 登录是否有效
    """
    import sys
    import os
    
    profile_dir = Path(profile_dir_path)
    
    # 1. 先检查 profile_dir 是否存在
    if not profile_dir.exists():
        print(f"❌ profile_dir 不存在: {profile_dir}", file=sys.__stdout__, flush=True)
        return False
    

    # 3. 查找 Cookies 文件（多种可能的路径）
    possible_cookie_paths = [
        profile_dir / "Default" / "Cookies",
        profile_dir / "Default" / "Network" / "Cookies",
        profile_dir / "Cookies",
    ]
    
    cookies_found = False
    for cookie_path in possible_cookie_paths:
        if cookie_path.exists():
            print(f"✅ 找到 Cookies 文件: {cookie_path}", file=sys.__stdout__, flush=True)
            cookies_found = True
            break
    
    if not cookies_found:
        print(f"⚠️ 未找到 Cookies 文件，但仍尝试浏览器验证...", file=sys.__stdout__, flush=True)
    
    # 4. 获取平台配置
    config = PLATFORM_CONFIG.get(platform_type)
    if not config:
        print(f"❌ 未知平台类型: {platform_type}", file=sys.__stdout__, flush=True)
        return False
    
    logger = config['logger']
    
    # 5. 使用 Playwright 启动持久化浏览器验证登录状态
    try:
        return await _verify_login_with_browser(profile_dir, config, logger)
    except Exception as e:
        logger.error(f"[x] 验证登录状态失败: {e}")
        return False


async def _verify_login_with_browser(profile_dir: Path, config: dict, logger) -> bool:
    """使用 Playwright 打开 UserDataDir 验证登录状态"""
    import sys
    
    async with async_playwright() as playwright:
        # 防风控隐藏指纹参数
        chrome_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-automation',
            '--disable-infobars',
            '--no-sandbox',
            '--no-first-run',
            '--lang=zh-CN',
        ]
        
        launch_options = {
            'headless': True,
            'args': chrome_args,
            'ignore_default_args': ['--enable-automation'],
        }
        
        if LOCAL_CHROME_PATH:
            launch_options['executable_path'] = LOCAL_CHROME_PATH
        
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                **launch_options,
                viewport={'width': 1280, 'height': 800},
                locale='zh-CN',
            )
            
            context = await set_init_script(context)
            page = context.pages[0] if context.pages else await context.new_page()
            
            try:
                # 尝试访问页面，最多重试2次
                max_retries = 2
                for attempt in range(max_retries + 1):
                    try:
                        await page.goto(config['url'], timeout=45000, wait_until='domcontentloaded')
                        break
                    except Exception as e:
                        if attempt < max_retries:
                            await asyncio.sleep(2)
                            continue
                        else:
                            raise e
                
                await asyncio.sleep(3)  # 等待页面加载
                
                current_url = page.url
                page_content = await page.content()
                
                # 1. 【优先】正向检测：检查是否有登录成功的标志
                # 先检测正向元素，避免登录页关键词在已登录页面也存在导致误判
                success_selectors = config.get('success_selectors', [])
                for selector in success_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            logger.success(f"[+] cookie 有效")
                            print(f"✅ Cookie 验证成功！", file=sys.__stdout__, flush=True)
                            return True
                    except:
                        pass
                
                # 2. URL 跳转检测
                if 'login_url_pattern' in config and config['login_url_pattern'] in current_url:
                    logger.error(f"[x] cookie 失效，跳转到了登录页")
                    print(f"❌ Cookie 验证失败！", file=sys.__stdout__, flush=True)
                    return False
                
                # 3. 检测登录页特征（负向检测）
                default_login_keywords = ['扫码登录', '验证码登录', '密码登录', '我是创作者', '我是MCN机构']
                login_page_keywords = config.get('login_page_keywords', default_login_keywords)
                if any(keyword in page_content for keyword in login_page_keywords):
                    logger.error(f"[x] cookie 失效，检测到登录页")
                    print(f"❌ Cookie 验证失败！", file=sys.__stdout__, flush=True)
                    return False
                
                # 4. 通用页面内容检测（备选）
                if not success_selectors:
                    if '发布' in page_content or '内容管理' in page_content:
                        logger.success(f"[+] cookie 有效")
                        print(f"✅ Cookie 验证成功！", file=sys.__stdout__, flush=True)
                        return True
                
                logger.error(f"[x] cookie 失效")
                return False
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.error(f"[x] 浏览器启动失败: {e}")
            return False


# 兼容旧接口
async def check_profile_dir(profile_dir: Path) -> bool:
    """简单检查 UserDataDir 是否存在有效数据（不验证登录状态）"""
    if not profile_dir.exists():
        return False
    
    cookies_file = profile_dir / "Default" / "Cookies"
    if cookies_file.exists() and cookies_file.stat().st_size > 0:
        return True
    
    cookies_file_alt = profile_dir / "Cookies"
    if cookies_file_alt.exists() and cookies_file_alt.stat().st_size > 0:
        return True
    
    return False
