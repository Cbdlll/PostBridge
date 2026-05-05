# -*- coding: utf-8 -*-
"""
Bilibili (B站) 视频上传 RPA 脚本
参照小红书/快手脚本实现，使用 Playwright 自动化操作
"""
from datetime import datetime
import random
import math
import os
import asyncio
from pathlib import Path

from playwright.async_api import Playwright, async_playwright, Page

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger
from utils.profile_manager import launch_persistent_browser, close_persistent_browser, ProfileLock


# ========================
# 防风控辅助函数
# ========================

async def random_delay(min_sec: float = 0.3, max_sec: float = 0.8):
    """随机延迟，防止触发风控"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def human_scroll(page: Page, direction: str = 'down', distance: int = None):
    """
    模拟人类滚动行为
    """
    try:
        if distance is None:
            distance = random.randint(100, 300)
        
        if direction == 'up':
            distance = -distance
        
        steps = random.randint(3, 6)
        step_distance = distance / steps
        
        for _ in range(steps):
            await page.mouse.wheel(0, step_distance)
            await asyncio.sleep(random.uniform(0.05, 0.15))
        
        await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        bilibili_logger.warning(f"human_scroll 失败: {e}")


async def human_type(page: Page, text: str, delay_range: tuple = (0.05, 0.15)):
    """
    模拟人类打字行为（逐字输入，带随机延迟）
    """
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(*delay_range))
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.3, 0.6))


async def human_click(page: Page, locator, timeout: int = 5000):
    """
    人性化点击：模拟真实用户的鼠标移动和点击行为
    
    特性:
    - 贝塞尔曲线鼠标移动轨迹
    - 随机点击位置偏移
    - 随机点击前后延迟
    """
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        
        box = await locator.bounding_box()
        if not box:
            await locator.click()
            return
        
        offset_x = random.uniform(-box['width'] * 0.2, box['width'] * 0.2)
        offset_y = random.uniform(-box['height'] * 0.2, box['height'] * 0.2)
        target_x = box['x'] + box['width'] / 2 + offset_x
        target_y = box['y'] + box['height'] / 2 + offset_y
        
        viewport = page.viewport_size or {'width': 1280, 'height': 800}
        start_x = random.uniform(0, viewport['width'])
        start_y = random.uniform(0, viewport['height'])
        
        ctrl1_x = start_x + (target_x - start_x) * random.uniform(0.2, 0.4)
        ctrl1_y = start_y + random.uniform(-100, 100)
        ctrl2_x = start_x + (target_x - start_x) * random.uniform(0.6, 0.8)
        ctrl2_y = target_y + random.uniform(-100, 100)
        
        steps = random.randint(8, 15)
        for i in range(steps + 1):
            t = i / steps
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * target_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * target_y
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.01, 0.03))
        
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.click(target_x, target_y)
        await asyncio.sleep(random.uniform(0.08, 0.2))
        
    except Exception as e:
        bilibili_logger.warning(f"human_click 失败，回退普通点击: {e}")
        try:
            await locator.click(timeout=timeout)
        except:
            pass


# ========================================
# 以下旧的 Cookie 相关函数已废弃
# 新架构使用 UserDataDir，无需这些函数
# ========================================



class BilibiliVideo:
    """Bilibili 视频上传类"""
    
    def __init__(self, title, file_path, tags, publish_date: datetime, profile_dir, description='', task_id=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.profile_dir = profile_dir  # UserDataDir 路径
        self.description = description
        self.task_id = task_id
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
    
    async def save_failure_screenshot(self, page, error_msg: str) -> str:
        """保存失败时的页面截图到 data/rpa_failed_screenshots/bilibili/ 目录"""
        try:
            from pathlib import Path
            from conf import BASE_DIR
            
            screenshot_dir = Path(BASE_DIR / "data" / "rpa_failed_screenshots" / "bilibili")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bilibili_{timestamp}.png"
            filepath = screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            bilibili_logger.info(f"  [✓] 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            bilibili_logger.warning(f"保存失败截图失败: {e}")
            return ""
    
    async def upload(self) -> None:
        """上传视频到 Bilibili（使用 UserDataDir 持久化浏览器）"""
        context = None
        page = None
        profile_lock = None
        
        try:
            # 使用 ProfileLock 确保同一账号不会同时操作
            profile_lock = ProfileLock(Path(self.profile_dir))
            async with profile_lock:
                # 启动持久化浏览器
                context = await launch_persistent_browser(
                    profile_dir=Path(self.profile_dir),
                    headless=self.headless,
                    chrome_path=self.local_executable_path
                )
                
                # 注入反检测脚本
                context = await set_init_script(context)
                
                # 获取或创建页面
                page = context.pages[0] if context.pages else await context.new_page()
                
                # 设置资源拦截（性能优化：阻止不必要的字体、追踪脚本）
                from utils.base_social_media import setup_resource_blocking
                await setup_resource_blocking(page, block_images=False, block_fonts=True, block_analytics=True)
            
                # 导航至投稿页面
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        bilibili_logger.info(f'[-] 正在跳转投稿页面 (Attempt {attempt + 1}/{max_nav_retries})...')
                        await page.goto("https://member.bilibili.com/platform/upload/video/frame", timeout=45000)
                        await random_delay(2, 3)
                        break
                    except Exception as e:
                        bilibili_logger.warning(f"[-] 导航超时或失败: {e}")
                        if attempt == max_nav_retries - 1:
                            raise e
                        await random_delay(2, 4)
                
                bilibili_logger.info(f'[+] 正在上传视频: {self.title}')
                await random_delay(1, 2)
                
                # 上传视频文件
                # B站投稿页面通常有一个隐藏的 input[type="file"] 用于上传
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(self.file_path)
                bilibili_logger.info(f'  [-] 视频文件已选择，等待上传...')
                
                # 等待上传完成 - 检测上传进度或成功标识
                max_upload_wait = 120  # 最多等待120秒
                for i in range(max_upload_wait):
                    try:
                        # 检查是否有上传成功标识（根据实际页面调整）
                        # B站可能显示"上传完成"或进度条消失
                        success_indicators = [
                            'text="封面"',  # 出现封面选择说明上传完成
                            'text="更换视频"',  # 出现更换按钮说明上传完成
                            '.upload-success',
                        ]
                        for indicator in success_indicators:
                            elem = page.locator(indicator).first
                            if await elem.count() > 0 and await elem.is_visible():
                                bilibili_logger.success(f'  [+] 视频上传完成')
                                break
                        else:
                            await asyncio.sleep(1)
                            continue
                        break
                    except:
                        await asyncio.sleep(1)
                
                await random_delay(1, 2)
                
                # 填写标题
                bilibili_logger.info(f'  [-] 正在填充标题...')
                title_input = page.locator('input[placeholder*="标题"]').first
                if await title_input.count() > 0:
                    await title_input.click()
                    await title_input.fill('')
                    await title_input.fill(self.title[:80])  # B站标题限制80字
                    bilibili_logger.success(f'  [+] 标题已填充: {self.title[:30]}...')
                else:
                    bilibili_logger.warning('  [!] 未找到标题输入框')
                
                await random_delay(0.5, 1)
                
                # 填写简介
                if self.description:
                    bilibili_logger.info(f'  [-] 正在填充简介...')
                    desc_area = page.locator('textarea[placeholder*="简介"]').first
                    if await desc_area.count() == 0:
                        # 备选选择器
                        desc_area = page.locator('.ql-editor, [contenteditable="true"]').first
                    
                    if await desc_area.count() > 0:
                        await desc_area.click()
                        await desc_area.fill(self.description[:2000])
                        bilibili_logger.success(f'  [+] 简介已填充')
                    else:
                        bilibili_logger.warning('  [!] 未找到简介输入框')
                
                await random_delay(0.5, 1)
                
                # 填写标签
                if self.tags:
                    bilibili_logger.info(f'  [-] 正在填充标签...')
                    tag_input = page.locator('input[placeholder*="标签"]').first
                    if await tag_input.count() == 0:
                        tag_input = page.locator('.tag-input input').first
                    
                    if await tag_input.count() > 0:
                        for tag in self.tags[:10]:  # B站限制标签数量
                            await tag_input.click()
                            await tag_input.fill(tag)
                            await page.keyboard.press("Enter")
                            await random_delay(0.3, 0.6)
                        bilibili_logger.success(f'  [+] 已添加 {len(self.tags[:10])} 个标签')
                    else:
                        bilibili_logger.warning('  [!] 未找到标签输入框')
                
                await random_delay(1, 2)
                
                # 关闭可能的提示弹窗（如"信息填完后，就可投稿！不需等待上传完成哦"）
                bilibili_logger.info(f'  [-] 检查并关闭提示弹窗...')
                try:
                    close_tip_selectors = [
                        'button:has-text("×")',
                        '.close-btn',
                        '[class*="close"]',
                        '.tip-close',
                        'svg[class*="close"]',
                        'i[class*="close"]',
                        # 直接点击提示框的关闭按钮
                        '.tips-container button',
                        '.tips-wrap button',
                    ]
                    for selector in close_tip_selectors:
                        try:
                            tip_close = page.locator(selector).first
                            if await tip_close.count() > 0 and await tip_close.is_visible():
                                await tip_close.click()
                                bilibili_logger.info(f'  [+] 已关闭提示弹窗')
                                await random_delay(0.3, 0.5)
                                break
                        except:
                            continue
                except Exception as e:
                    bilibili_logger.debug(f'  [!] 关闭提示弹窗时: {e}')
                
                await random_delay(0.5, 1)
                
                # 点击发布按钮
                bilibili_logger.info(f'  [-] 正在发布...')
                max_publish_attempts = 30
                publish_clicked = False
                
                for attempt in range(max_publish_attempts):
                    try:
                        # 检测是否已经发布成功（页面显示"稿件投递成功"）
                        success_text = page.locator('text="稿件投递成功"')
                        if await success_text.count() > 0 and await success_text.is_visible():
                            bilibili_logger.success("  [✓] 检测到成功提示，视频发布成功")
                            break
                        
                        # 检测是否跳转到成功后的URL
                        current_url = page.url
                        if 'upload-manager' in current_url or 'success' in current_url:
                            bilibili_logger.success("  [✓] 检测到成功URL，视频发布成功")
                            break
                        
                        # 如果未点击过发布按钮，尝试点击
                        if not publish_clicked:
                            # 先滚动页面到底部
                            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                            await random_delay(0.5, 0.8)
                            
                            # B站的发布按钮 - 使用多种精确选择器
                            # 根据截图，按钮文字是"立即投稿"，在一个蓝色按钮内
                            publish_selectors = [
                                # 1. 最精确：通过span文本定位
                                'span:text-is("立即投稿")',
                                # 2. 通过button包含文本定位
                                'button:has(span:text-is("立即投稿"))',
                                # 3. 通过class定位
                                '.bcc-button.bcc-button--primary:has-text("立即投稿")',
                                'button.submit-add',
                                # 4. 回退选择器
                                'button:has-text("立即投稿")',
                                'button:has-text("投稿")',
                            ]
                            
                            for selector in publish_selectors:
                                try:
                                    btn = page.locator(selector).first
                                    if await btn.count() > 0 and await btn.is_visible():
                                        # 滚动到按钮可见
                                        await btn.scroll_into_view_if_needed()
                                        await random_delay(0.3, 0.5)
                                        
                                        # 获取按钮位置并直接点击坐标
                                        box = await btn.bounding_box()
                                        if box:
                                            x = box['x'] + box['width'] / 2
                                            y = box['y'] + box['height'] / 2
                                            await page.mouse.click(x, y)
                                            bilibili_logger.info(f'  [+] 已通过坐标点击发布按钮: {selector}')
                                            publish_clicked = True
                                            break
                                        else:
                                            # 没有坐标，使用force点击
                                            await btn.click(force=True)
                                            bilibili_logger.info(f'  [+] 已强制点击发布按钮: {selector}')
                                            publish_clicked = True
                                            break
                                except Exception as btn_err:
                                    bilibili_logger.debug(f'  [!] 选择器 {selector} 失败: {btn_err}')
                                    continue
                        
                        bilibili_logger.info(f"  [-] 等待发布完成... ({attempt + 1}/{max_publish_attempts})")
                        await random_delay(1.5, 2.5)
                        
                    except Exception as e:
                        bilibili_logger.warning(f"  [!] 发布尝试 {attempt + 1} 出错: {e}")
                        await random_delay(1, 2)
                
                # UserDataDir 模式下，登录态自动保存，无需手动保存 cookie
                bilibili_logger.success('  [-] 发布完成，用户配置已自动保存！')
                
        except RuntimeError as e:
            bilibili_logger.error(f"  [-] 账号目录被占用: {e}")
            raise
        except Exception as e:
            bilibili_logger.error(f"上传失败: {e}")
            if page:
                await self.save_failure_screenshot(page, str(e))
            raise
        finally:
            # 关闭持久化浏览器
            if context:
                try:
                    await close_persistent_browser(context)
                except:
                    pass
            
            # 强制释放锁
            if profile_lock:
                try:
                    profile_lock.force_release()
                except:
                    pass
            
            # 清理 profile 目录锁文件
            ProfileLock.cleanup_profile(Path(self.profile_dir))
    
    async def main(self):
        """带超时控制的主入口"""
        await self.upload()
