# -*- coding: utf-8 -*-
from datetime import datetime
import random
import math
from pathlib import Path

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
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
    
    Args:
        page: Playwright页面对象
        direction: 滚动方向 'up' 或 'down'
        distance: 滚动距离（像素），None则随机
    """
    try:
        if distance is None:
            distance = random.randint(100, 300)
        
        if direction == 'up':
            distance = -distance
        
        # 分多步滚动，模拟人类行为
        steps = random.randint(3, 6)
        step_distance = distance / steps
        
        for _ in range(steps):
            await page.mouse.wheel(0, step_distance)
            await asyncio.sleep(random.uniform(0.05, 0.15))
        
        await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        douyin_logger.warning(f"human_scroll 失败: {e}")


async def human_type(page: Page, text: str, delay_range: tuple = (0.05, 0.15)):
    """
    模拟人类打字行为（逐字输入，带随机延迟）
    
    Args:
        page: Playwright页面对象
        text: 要输入的文本
        delay_range: 每个字符之间的延迟范围（秒）
    """
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(*delay_range))
        # 偶尔加入更长延迟（模拟思考）
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
        # 等待元素可见
        await locator.wait_for(state="visible", timeout=timeout)
        
        # 获取元素边界框
        box = await locator.bounding_box()
        if not box:
            # 回退到普通点击
            await locator.click()
            return
        
        # 计算随机点击位置（不总是点击中心）
        offset_x = random.uniform(-box['width'] * 0.2, box['width'] * 0.2)
        offset_y = random.uniform(-box['height'] * 0.2, box['height'] * 0.2)
        target_x = box['x'] + box['width'] / 2 + offset_x
        target_y = box['y'] + box['height'] / 2 + offset_y
        
        # 获取当前鼠标位置（模拟从随机位置开始）
        viewport = page.viewport_size or {'width': 1280, 'height': 800}
        start_x = random.uniform(0, viewport['width'])
        start_y = random.uniform(0, viewport['height'])
        
        # 生成贝塞尔曲线控制点
        ctrl1_x = start_x + (target_x - start_x) * random.uniform(0.2, 0.4)
        ctrl1_y = start_y + random.uniform(-100, 100)
        ctrl2_x = start_x + (target_x - start_x) * random.uniform(0.6, 0.8)
        ctrl2_y = target_y + random.uniform(-100, 100)
        
        # 沿贝塞尔曲线移动鼠标（8-15步）
        steps = random.randint(8, 15)
        for i in range(steps + 1):
            t = i / steps
            # 三次贝塞尔曲线公式
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * target_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * target_y
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.01, 0.03))
        
        # 点击前随机短暂停顿
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # 点击
        await page.mouse.click(target_x, target_y)
        
        # 点击后短暂停顿
        await asyncio.sleep(random.uniform(0.08, 0.2))
        
    except Exception as e:
        douyin_logger.warning(f"human_click 失败，回退普通点击: {e}")
        try:
            await locator.click(timeout=timeout)
        except:
            pass


# ========================================
# 以下旧的 Cookie 相关函数已废弃
# 新架构使用 UserDataDir，无需这些函数
# ========================================



class DouYinVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, profile_dir, thumbnail_path=None, description='', verification_queue=None, task_id=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.profile_dir = profile_dir  # UserDataDir 路径
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path
        self.description = description  # 视频简介
        self.verification_queue = verification_queue  # 验证码队列
        self.task_id = task_id  # 任务ID，用于前端通知

    async def set_schedule_time_douyin(self, page, publish_date):
        # 选择包含特定文本内容的 label 元素
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await human_click(page, label_element)
        await random_delay(0.5, 1.0)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await random_delay(0.3, 0.6)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await random_delay(0.5, 1.0)

    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def update_status(self, progress: int, error_msg: str = None):
        """更新数据库中的任务进度（支持手动发布和AI任务）"""
        if not self.task_id:
            return
            
        try:
            import sqlite3
            from conf import BASE_DIR, DATABASE_PATH
            from pathlib import Path
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                if self.task_id.startswith('manual_'):
                    # 手动发布任务
                    db_id = int(self.task_id.split('_')[1])
                    if error_msg:
                        cursor.execute(
                            'UPDATE publish_tasks SET progress = ?, status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                            (progress, 'failed', error_msg, db_id)
                        )
                    else:
                        cursor.execute(
                            'UPDATE publish_tasks SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                            (progress, db_id)
                        )
                elif self.task_id.startswith('ai_'):
                    # AI 获客任务
                    db_id = int(self.task_id.split('_')[1])
                    if error_msg:
                        cursor.execute(
                            'UPDATE creation_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                            ('video_failed', error_msg, db_id)
                        )
                    # AI任务进度通过status字段表示，不使用progress
                    
                conn.commit()
        except Exception as e:
            douyin_logger.warning(f"更新任务进度失败: {e}")

    async def update_verification_status(self, need_verification: bool):
        """更新任务的验证码状态"""
        if not self.task_id:
            return
        
        try:
            import sqlite3
            from conf import BASE_DIR, DATABASE_PATH
            from pathlib import Path
            
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                status = 'need_verification' if need_verification else 'running'
                
                if self.task_id.startswith('manual_'):
                    db_id = int(self.task_id.split('_')[1])
                    cursor.execute(
                        'UPDATE publish_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, db_id)
                    )
                elif self.task_id.startswith('ai_'):
                    db_id = int(self.task_id.split('_')[1])
                    cursor.execute(
                        'UPDATE creation_tasks SET publish_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                        (status, db_id)
                    )
                conn.commit()
                douyin_logger.info(f"  [✓] 任务状态已更新: {status}")
        except Exception as e:
            douyin_logger.warning(f"更新验证码状态失败: {e}")

    async def save_failure_screenshot(self, page, error_msg: str) -> str:
        """保存失败时的页面截图到 data/rpa_failed_screenshots/douyin/ 目录"""
        try:
            from datetime import datetime
            from pathlib import Path
            from conf import BASE_DIR
            
            screenshot_dir = Path(BASE_DIR / "data" / "rpa_failed_screenshots" / "douyin")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            task_id_safe = self.task_id.replace('/', '_') if self.task_id else 'unknown'
            filename = f"{task_id_safe}_{timestamp}.png"
            filepath = screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            douyin_logger.info(f"  [✓] 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            douyin_logger.warning(f"保存失败截图失败: {e}")
            return ""

    async def upload(self) -> None:
        """上传视频到抖音（使用 UserDataDir 持久化浏览器）"""
        context = None
        page = None  # 用于失败截图
        profile_lock = None  # 显式管理锁
        profile_path = Path(self.profile_dir)
        
        try:
            # 使用 ProfileLock 确保同一账号不会同时操作
            profile_lock = ProfileLock(profile_path)
            async with profile_lock:
                # 启动持久化浏览器
                context = await launch_persistent_browser(
                    profile_dir=profile_path,
                    headless=self.headless,
                    chrome_path=self.local_executable_path
                )
                
                # 注入反检测脚本
                from utils.base_social_media import set_init_script
                context = await set_init_script(context)
                
                await self.update_status(10)

                # 获取或创建页面
                page = context.pages[0] if context.pages else await context.new_page()
                
                # 设置资源拦截（性能优化：阻止不必要的图片、字体、追踪脚本）
                from utils.base_social_media import setup_resource_blocking
                await setup_resource_blocking(page, block_images=False, block_fonts=True, block_analytics=True)
                
                # 导航重试机制
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        douyin_logger.info(f'[-] 正在跳转上传也 (Attempt {attempt + 1}/{max_nav_retries})...')
                        await page.goto("https://creator.douyin.com/creator-micro/content/upload", timeout=45000) # 增加单次超时时间
                        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=30000)
                        break 
                    except Exception as e:
                        douyin_logger.warning(f"[-] 导航超时或失败: {e}")
                        if attempt == max_nav_retries - 1:
                            douyin_logger.error("[-] 导航最终失败，放弃本次任务")
                            raise e 
                        await random_delay(2, 4)
                        # 尝试刷新或重新加载 (goto会重新加载)

                douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
                await self.update_status(20)
                # 使用更精确的选择器定位视频上传输入框
                video_upload_input = page.locator('input[type="file"][accept*="video"]').first
                await video_upload_input.set_input_files(self.file_path)
                await self.update_status(40)
                douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
                # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
                douyin_logger.info(f'[-] 正在打开主页...')
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
                # 点击 "上传视频" 按钮（如果需要重新上传）
                # await video_upload_input.set_input_files(self.file_path)

                # 等待页面跳转到指定的 URL 2025.01.08修改在原有基础上兼容两种页面
                while True:
                    try:
                        # 尝试等待第一个 URL
                        await page.wait_for_url(
                            "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page", timeout=3000)
                        douyin_logger.info("[+] 成功进入version_1发布页面!")
                        break  # 成功进入页面后跳出循环
                    except Exception:
                        try:
                            # 如果第一个 URL 超时，再尝试等待第二个 URL
                            await page.wait_for_url(
                                "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                                timeout=3000)
                            douyin_logger.info("[+] 成功进入version_2发布页面!")

                            break  # 成功进入页面后跳出循环
                        except:
                            print("  [-] 超时未进入视频发布页面，重新尝试...")
                            await random_delay(0.3, 0.6)
                # 填充标题和简介
                await random_delay(0.5, 1.0)
                douyin_logger.info(f'  [-] 正在填充标题和简介...')
                
                # 1. 填充作品标题（上方小输入框）
                try:
                    # 方法1: 通过placeholder定位标题输入框
                    title_input = page.locator('input[placeholder*="填写作品标题"]').first
                    if await title_input.count() > 0:
                        await title_input.fill(self.title)
                        douyin_logger.success(f'  [+] 标题已填充: {self.title}')
                    else:
                        # 方法2: 通过文本"作品标题"定位
                        title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
                        if await title_container.count():
                            await title_container.fill(self.title)
                            douyin_logger.success(f'  [+] 标题已填充: {self.title}')
                        else:
                            douyin_logger.warning('  [!] 未找到标题输入框')
                except Exception as e:
                    douyin_logger.error(f'  [-] 填充标题失败: {e}')
                
                # 2. 填充作品描述（下方大文本框，如果有简介）
                if self.description:
                    try:
                        # 定位作品描述区域（.notranslate 或 .zone-container）
                        desc_container = page.locator(".notranslate").first
                        if await desc_container.count() > 0:
                            await human_click(page, desc_container)
                            await random_delay(0.2, 0.4)
                            # 清空已有内容
                            await page.keyboard.press("Control+KeyA")
                            await page.keyboard.press("Delete")
                            # 填充简介
                            await page.keyboard.type(self.description)
                            douyin_logger.success(f'  [+] 简介已填充')
                        else:
                            douyin_logger.warning('  [!] 未找到描述输入框')
                    except Exception as e:
                        douyin_logger.error(f'  [-] 填充简介失败: {e}')
                
                # 3. 添加话题标签
                css_selector = ".zone-container"
                for index, tag in enumerate(self.tags, start=1):
                    await page.type(css_selector, "#" + tag)
                    await page.press(css_selector, "Space")
                douyin_logger.info(f'总共添加{len(self.tags)}个话题')
                while True:
                    # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
                    try:
                        #  新版：定位重新上传
                        number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                        if number > 0:
                            douyin_logger.success("  [-]视频上传完毕")
                            break
                        else:
                            douyin_logger.info("  [-] 正在上传视频中...")
                            await random_delay(1.5, 2.5)

                            if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                                douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                                await self.handle_upload_error(page)
                    except:
                        douyin_logger.info("  [-] 正在上传视频中...")
                        await random_delay(1.5, 2.5)

                # 检测并关闭"设置竖封面获更多流量"弹窗
                try:
                    popup_dismiss_btn = page.locator('text="暂不设置"').first
                    if await popup_dismiss_btn.count() > 0:
                        await human_click(page, popup_dismiss_btn)
                        douyin_logger.info("  [+] 已关闭'设置竖封面获更多流量'弹窗")
                        await random_delay(0.5, 1.0)
                except Exception as e:
                    pass  # 没有弹窗则继续

                # 自动设置封面流程（跳过封面提取，直接使用抖音默认封面+无模板）
                await self.auto_set_cover_and_publish(page)


                # 更换可见元素
                await self.set_location(page, "")


                # 頭條/西瓜
                third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
                # 定位是否有第三方平台
                if await page.locator(third_part_element).count():
                    # 检测是否是已选中状态 (使用原生API替代JS)
                    switch_class = await page.locator(third_part_element).get_attribute('class') or ''
                    if 'semi-switch-checked' not in switch_class:
                        await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

                if self.publish_date != 0:
                    await self.set_schedule_time_douyin(page, self.publish_date)

                # 等待发布成功（页面跳转到作品管理页面）
                max_wait_attempts = 30  # 最多等待30次
                verification_passed = False  # 标记验证是否已通过
                for attempt in range(max_wait_attempts):
                    # 检测是否出现验证码弹窗（如果验证已通过则跳过检测）
                    if not verification_passed:
                        need_verify, verify_success = await self.check_verification_code(page)
                        if need_verify:
                            if verify_success:
                                # 验证成功，标记并继续等待页面跳转
                                verification_passed = True
                                douyin_logger.info("  [+] 验证已完成，继续等待发布...")
                            else:
                                # 验证失败或等待中
                                douyin_logger.warning("  [!] 检测到需要验证码验证，请在浏览器中完成验证后继续...")
                                await random_delay(2.0, 3.5)
                                continue
                    
                    try:
                        # 等待页面跳转到作品管理页面
                        await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**",
                                                timeout=3000)
                        douyin_logger.success("  [+] 视频发布成功！")
                        break
                    except:
                        douyin_logger.info(f"  [-] 等待发布完成... ({attempt + 1}/{max_wait_attempts})")
                        await random_delay(0.5, 1.0)

                # UserDataDir 模式下，登录态自动保存，无需手动保存 cookie
                douyin_logger.success('  [-] 发布完成，用户配置已自动保存！')
                await random_delay(0.3, 0.5)
                
        except RuntimeError as e:
            douyin_logger.error(f"  [-] 账号目录被占用: {e}")
            raise
        except Exception as e:
            # 保存失败截图
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
            
            # 强制清理锁（确保即使 async with 失败也能释放）
            if profile_lock:
                try:
                    profile_lock.force_release()
                except:
                    pass
            # 兜底：直接清理配置目录锁文件
            ProfileLock.cleanup_profile(profile_path)

    async def auto_set_cover_and_publish(self, page, max_retries: int = 3) -> bool:
        """
        自动设置封面并发布流程（按截图顺序）：
        1. 点击"选择封面"按钮（横封面4:3）
        2. 点击"无模板"选项
        3. 点击"设置竖封面"按钮
        4. 点击"无模板"选项（竖封面界面）
        5. 点击"完成"按钮
        6. 点击底部"发布"按钮
        
        Args:
            page: Playwright页面对象
            max_retries: 最大重试次数
        
        Returns:
            是否成功
        """
        for attempt in range(max_retries):
            try:
                douyin_logger.info(f"  [-] 开始设置封面流程 (尝试 {attempt + 1}/{max_retries})...")
                
                # ========== Step 1: 点击"选择封面"按钮 ==========
                select_cover_btn = page.locator('text="选择封面"').first
                if await select_cover_btn.count() == 0:
                    douyin_logger.warning("  [!] 未找到选择封面按钮")
                    continue
                await human_click(page, select_cover_btn)
                douyin_logger.info("  [1/5] 已点击选择封面按钮")
                
                # 验证：等待封面模态框出现
                try:
                    await page.wait_for_selector("div.dy-creator-content-modal", timeout=5000)
                    douyin_logger.info("  [1/5] ✓ 封面模态框已出现")
                except:
                    douyin_logger.warning("  [!] 封面模态框未出现，重试")
                    continue
                
                await random_delay(0.5, 0.8)
                
                # ========== Step 2: 点击"设置竖封面"按钮 ==========
                vertical_cover_btn = page.locator('text="设置竖封面"').first
                if await vertical_cover_btn.count() == 0:
                    douyin_logger.warning("  [!] 未找到设置竖封面按钮")
                    continue
                await human_click(page, vertical_cover_btn)
                douyin_logger.info("  [2/5] 已点击设置竖封面按钮")
                
                # 验证：等待竖封面标签被激活
                await random_delay(0.8, 1.2)
                douyin_logger.info("  [2/5] ✓ 竖封面设置界面已加载")
                
                # ========== Step 3: 点击"设置横封面"按钮 ==========
                horizontal_cover_btn = page.locator('text="设置横封面"').first
                if await horizontal_cover_btn.count() == 0:
                    douyin_logger.warning("  [!] 未找到设置横封面按钮")
                    continue
                await human_click(page, horizontal_cover_btn)
                douyin_logger.info("  [3/5] 已点击设置横封面按钮")
                
                # 验证：等待横封面标签被激活
                await random_delay(0.8, 1.2)
                douyin_logger.info("  [3/5] ✓ 横封面设置界面已加载")
                
                # ========== Step 4: 点击"完成"按钮 ==========
                finish_btn = page.locator('button:has-text("完成")').last
                if await finish_btn.count() == 0:
                    douyin_logger.warning("  [!] 未找到完成按钮")
                    continue
                await human_click(page, finish_btn)
                douyin_logger.info("  [4/5] 已点击完成按钮")
                
                # 验证：等待模态框完全关闭
                try:
                    await page.wait_for_selector("div.dy-creator-content-modal", state='hidden', timeout=5000)
                    douyin_logger.info("  [4/5] ✓ 封面模态框已关闭")
                except:
                    douyin_logger.warning("  [!] 封面模态框未关闭，尝试继续")
                
                await random_delay(0.8, 1.2)
                
                # ========== Step 4: 点击底部"发布"按钮 ==========
                # 先处理可能的弹窗（权限弹窗、新手引导等）
                try:
                    # 关闭"我知道了"类型的新手引导弹窗
                    guide_dismiss_selectors = [
                        'button:has-text("我知道了")',
                        'button:has-text("知道了")',
                        'button:has-text("好的")',
                        'button:has-text("确定")',
                        '.semi-button:has-text("我知道了")',
                        '[class*="guide"] button',
                        '[class*="tooltip"] button',
                    ]
                    for selector in guide_dismiss_selectors:
                        try:
                            dismiss_btn = page.locator(selector).first
                            if await dismiss_btn.count() > 0 and await dismiss_btn.is_visible():
                                await dismiss_btn.click()
                                douyin_logger.info(f"  [5/5] 已关闭引导弹窗: {selector}")
                                await random_delay(0.3, 0.5)
                                break
                        except:
                            continue
                            
                    # 关闭浏览器权限弹窗（地理位置等）
                    permission_dismiss_selectors = [
                        'button:has-text("Never allow")',
                        'button:has-text("Block")',
                        'button:has-text("不允许")',
                        'button:has-text("拒绝")',
                    ]
                    for selector in permission_dismiss_selectors:
                        try:
                            dismiss_btn = page.locator(selector).first
                            if await dismiss_btn.count() > 0 and await dismiss_btn.is_visible():
                                await dismiss_btn.click()
                                douyin_logger.info(f"  [5/5] 已关闭权限弹窗: {selector}")
                                await random_delay(0.3, 0.5)
                                break
                        except:
                            continue
                except Exception as e:
                    douyin_logger.debug(f"  [!] 关闭弹窗时: {e}")
                
                await random_delay(0.5, 0.8)
                
                # 使用 Playwright 原生定位发布按钮
                publish_clicked = False
                try:
                    # 策略1: 精确 CSS 选择器定位红色发布按钮（最可靠）
                    # 抖音的红色按钮类名包含 semi-button-danger
                    danger_btn = page.locator('button.semi-button-danger').filter(has_text="发布").first
                    if await danger_btn.count() > 0:
                        await danger_btn.scroll_into_view_if_needed()
                        await random_delay(0.2, 0.4)
                        # 使用 force=True 强制点击，绕过可能的遮挡
                        await danger_btn.click(force=True)
                        publish_clicked = True
                        douyin_logger.info("  [5/5] 已点击发布按钮 (semi-button-danger)")
                    
                    # 策略2: 通过按钮样式定位（primary 类型）
                    if not publish_clicked:
                        primary_btn = page.locator('button.semi-button-primary').filter(has_text="发布").first
                        if await primary_btn.count() > 0:
                            await primary_btn.scroll_into_view_if_needed()
                            await random_delay(0.2, 0.4)
                            await primary_btn.click(force=True)
                            publish_clicked = True
                            douyin_logger.info("  [5/5] 已点击发布按钮 (semi-button-primary)")
                    
                    # 策略3: 通过位置筛选（页面下半部分的发布按钮）
                    if not publish_clicked:
                        all_publish_btns = page.locator('button:has-text("发布")')
                        count = await all_publish_btns.count()
                        for i in range(count):
                            btn = all_publish_btns.nth(i)
                            if not await btn.is_visible():
                                continue
                            box = await btn.bounding_box()
                            # 过滤：x > 200（排除左侧导航），y > 400（页面下半部分）
                            if box and box['x'] > 200 and box['y'] > 400:
                                await btn.scroll_into_view_if_needed()
                                await btn.click(force=True)
                                publish_clicked = True
                                douyin_logger.info(f"  [5/5] 已点击发布按钮 (位置定位: x={int(box['x'])}, y={int(box['y'])})")
                                break
                    
                    # 策略4: 使用 get_by_role 定位
                    if not publish_clicked:
                        role_btn = page.get_by_role("button", name="发布", exact=True)
                        if await role_btn.count() > 0:
                            # 筛选可见且在右侧的按钮
                            for i in range(await role_btn.count()):
                                btn = role_btn.nth(i)
                                if await btn.is_visible():
                                    box = await btn.bounding_box()
                                    if box and box['x'] > 200:
                                        await btn.click(force=True)
                                        publish_clicked = True
                                        douyin_logger.info("  [5/5] 已点击发布按钮 (get_by_role)")
                                        break
                    
                    if publish_clicked:
                        douyin_logger.success("  [+] 封面设置并发布流程完成!")
                        return True
                                 
                except Exception as e:
                    douyin_logger.warning(f"  [!] 原生定位发布按钮尝试失败: {e}")

                douyin_logger.warning("  [!] 未找到底部发布按钮")
                continue
                
            except Exception as e:
                douyin_logger.error(f"  [-] 封面设置流程出错 (尝试 {attempt + 1}): {e}")
                await random_delay(0.5, 1.0)
        
        douyin_logger.error("  [-] 封面设置流程失败")
        return False

    async def check_verification_code(self, page: Page) -> tuple:
        """
        检测页面是否出现验证码弹窗
        返回 (need_verification, verification_success) 元组：
        - (False, False): 不需要验证码
        - (True, True): 需要验证码且验证成功
        - (True, False): 需要验证码但验证失败/未完成
        """
        # 检测常见的验证码相关文本
        verification_texts = [
            "验证码",
            "手机验证", 
            "安全验证",
            "滑动验证",
            "请完成验证",
            "人机验证"
        ]
        
        for text in verification_texts:
            try:
                if await page.get_by_text(text).first.is_visible():
                    douyin_logger.warning(f"  [!] 检测到验证提示: {text}")
                    # 如果有验证码队列，通知前端并等待用户输入
                    if self.verification_queue:
                        verify_success = await self.handle_verification_input(page)
                        return (True, verify_success)
                    return (True, False)
            except:
                pass
        
        # 检测验证码iframe
        iframe_selectors = [
            'iframe[id*="verify"]',
            'iframe[id*="captcha"]',
            'iframe[class*="verify"]'
        ]
        
        for selector in iframe_selectors:
            if await page.locator(selector).count() > 0:
                douyin_logger.warning(f"  [!] 检测到验证iframe: {selector}")
                if self.verification_queue:
                    verify_success = await self.handle_verification_input(page)
                    return (True, verify_success)
                return (True, False)
        
        return (False, False)

    async def handle_verification_input(self, page: Page):
        """
        处理验证码输入：通知前端并等待用户输入验证码
        支持验证失败后重新输入
        """
        try:
            # 0. 更新数据库状态为 need_verification
            await self.update_verification_status(True)
            
            # 1. 尝试自动点击 "获取验证码"
            try:
                get_code_btns = [
                    'text="获取验证码"',
                    'text="发送验证码"',
                    'button:has-text("获取验证码")',
                    'span:has-text("获取验证码")'
                ]
                
                for btn_selector in get_code_btns:
                    btn = page.locator(btn_selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        douyin_logger.info("  [+] 已自动点击'获取验证码'")
                        await asyncio.sleep(1)
                        break
            except Exception as e:
                douyin_logger.warning(f"  [!] 点击获取验证码失败: {e}")

            # 2. 通知前端需要验证码
            from utils.global_state import active_queues
            if self.task_id and f"verify_{self.task_id}" in active_queues:
                notify_queue = active_queues[f"verify_{self.task_id}"]
                notify_queue.put("NEED_VERIFICATION")
                douyin_logger.info("  [!] 已通知前端需要验证码")
            else:
                douyin_logger.warning(f"  [!] 未找到通知队列: verify_{self.task_id}")
            
            # 3. 等待用户输入验证码 - 支持重试
            import queue
            max_retries = 3  # 最多重试 3 次
            for retry in range(max_retries):
                douyin_logger.info(f"  [!] 等待用户输入验证码... (尝试 {retry + 1}/{max_retries})")
                try:
                    code = self.verification_queue.get(timeout=180)  # 增加超时时间
                    douyin_logger.info(f"  [+] 收到验证码: {code}")
                    
                    # 填充并验证
                    verify_success = await self._fill_and_submit_verification(page, code)
                    
                    if verify_success:
                        # 验证成功，更新状态并通知前端
                        await self.update_verification_status(False)
                        if self.task_id and f"verify_{self.task_id}" in active_queues:
                            active_queues[f"verify_{self.task_id}"].put("VERIFICATION_SUCCESS")
                        douyin_logger.success("  [✓] 验证码验证成功!")
                        return True  # 返回验证成功
                    else:
                        # 验证失败，通知前端重新输入
                        if self.task_id and f"verify_{self.task_id}" in active_queues:
                            active_queues[f"verify_{self.task_id}"].put("VERIFICATION_FAILED")
                        douyin_logger.warning("  [!] 验证码验证失败，请重新输入")
                        
                except queue.Empty:
                    douyin_logger.error("  [-] 等待验证码超时")
                    break
            
            # 所有重试失败
            douyin_logger.error("  [-] 验证码验证最终失败")
            return False  # 返回验证失败
                
        except Exception as e:
            douyin_logger.error(f"  [-] 处理验证码时出错: {e}")
            return False  # 异常也返回失败

    async def _fill_and_submit_verification(self, page: Page, code: str) -> bool:
        """填充验证码并提交，返回是否验证成功"""
        try:
            # 查找验证码输入框
            verification_input = None
            input_selectors = [
                'input[placeholder*="验证码"]',
                'input[placeholder*="请输入"]',
                'input[type="text"][class*="verify"]',
                'input[class*="code"]',
                'input[type="tel"]',
                'input[type="number"]',
            ]
            
            for selector in input_selectors:
                try:
                    input_elem = page.locator(selector).first
                    if await input_elem.count() > 0 and await input_elem.is_visible():
                        verification_input = input_elem
                        douyin_logger.info(f"  [+] 找到验证码输入框: {selector}")
                        break
                except:
                    continue
            
            if not verification_input:
                douyin_logger.error("  [-] 未找到验证码输入框")
                return False
            
            # 填充验证码
            await verification_input.click()
            await verification_input.fill(str(code))
            await verification_input.dispatch_event('input')
            await verification_input.dispatch_event('change')
            await asyncio.sleep(0.5)
            
            douyin_logger.success(f"  [+] 验证码已填充: {code}")
            
            # 点击验证按钮
            await asyncio.sleep(1.5)
            await self._click_verify_button(page)
            
            # 检查验证结果：等待验证码弹窗消失或错误提示出现
            await asyncio.sleep(2)
            
            # 检测错误提示
            error_texts = ["验证码错误", "验证码不正确", "请重新输入", "验证失败"]
            for err_text in error_texts:
                if await page.get_by_text(err_text).first.is_visible():
                    return False
            
            # 检测验证码弹窗是否仍然存在
            verification_texts = ["验证码", "手机验证", "安全验证"]
            for v_text in verification_texts:
                try:
                    if await page.get_by_text(v_text).first.is_visible():
                        # 验证码弹窗还在，可能验证失败
                        return False
                except:
                    pass
            
            # 验证码弹窗消失，认为验证成功
            return True
            
        except Exception as e:
            douyin_logger.error(f"  [-] 填充验证码时出错: {e}")
            return False

    async def _click_verify_button(self, page: Page):
        """
        点击验证按钮
        策略：
        1. 先尝试 Playwright 原生 locator（高效但可能无法识别某些动态元素）
        2. 再尝试 Playwright 底层 API 遍历元素
        3. 最后使用 JavaScript 遍历 DOM（最可靠但有风控风险）
        """
        douyin_logger.info("  [-] 尝试查找并点击验证按钮...")
        
        # ========== 策略1: Playwright 原生 locator ==========
        try:
            # 尝试多种选择器
            selectors = [
                'button.semi-button-danger:has-text("验证")',
                'button.semi-button-primary:has-text("验证")',
                'button:has-text("验证"):not(:has-text("获取")):not(:has-text("发送"))',
                '.semi-modal button:has-text("验证")',
            ]
            
            for selector in selectors:
                try:
                    btn = page.locator(selector).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click(force=True)
                        douyin_logger.success(f"  [+] Playwright locator 点击成功: {selector}")
                        return
                except Exception:
                    continue
        except Exception as e:
            douyin_logger.debug(f"  [!] Playwright locator 策略失败: {e}")
        
        # ========== 策略2: Playwright 底层 API 遍历 ==========
        # 使用 query_selector_all 获取原始 ElementHandle，可以访问更底层的属性
        try:
            douyin_logger.info("  [-] 尝试 Playwright 底层 API 遍历元素...")
            
            # 获取所有 button 元素
            buttons = await page.query_selector_all('button')
            for btn in buttons:
                try:
                    text = await btn.inner_text()
                    text = text.strip() if text else ""
                    
                    # 精确匹配"验证"，排除"获取验证码"等
                    if text == "验证":
                        box = await btn.bounding_box()
                        if box and box['width'] > 0 and box['height'] > 0:
                            await btn.click(force=True)
                            douyin_logger.success(f"  [+] Playwright ElementHandle 点击成功: '{text}'")
                            return
                except Exception:
                    continue
            
            # 尝试 span 和 div 元素（某些按钮可能用这些标签）
            for tag in ['span', 'div']:
                elements = await page.query_selector_all(tag)
                for el in elements:
                    try:
                        text = await el.inner_text()
                        text = text.strip() if text else ""
                        
                        if text == "验证":
                            box = await el.bounding_box()
                            if box and box['width'] > 0 and box['height'] > 0:
                                await el.click(force=True)
                                douyin_logger.success(f"  [+] Playwright ElementHandle 点击成功: '{tag}' -> '{text}'")
                                return
                    except Exception:
                        continue
                        
        except Exception as e:
            douyin_logger.debug(f"  [!] Playwright 底层 API 策略失败: {e}")
        
        # ========== 策略3: JavaScript 遍历 DOM（最可靠） ==========
        douyin_logger.info("  [-] Playwright 方案失败，使用 JavaScript 遍历 DOM...")
        
        js_result = await page.evaluate('''() => {
            const result = { found: false, clicked: false, buttonText: '', debug: [] };
            
            // 遍历整个页面的所有元素
            const allElements = document.querySelectorAll('*');
            
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                const tagName = el.tagName.toLowerCase();
                
                // 查找包含"验证"文本的按钮类元素（精确匹配，排除"获取验证码"等）
                if (text === '验证' && (tagName === 'button' || tagName === 'span' || tagName === 'div')) {
                    if (text.length <= 4) {
                        result.debug.push(`找到元素: ${tagName}, text="${text}"`);
                        
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden') {
                            result.found = true;
                            result.buttonText = text;
                            
                            try {
                                el.click();
                                result.debug.push('el.click() 执行');
                            } catch(e) { result.debug.push('click失败: ' + e.message); }
                            
                            result.clicked = true;
                            return result;
                        }
                    }
                }
            }
            
            // 备用方案：查找确认按钮
            if (!result.found) {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = (btn.innerText || '').trim();
                    if ((text === '验证' || text === '确定' || text === '确认') && text !== '取消') {
                        result.debug.push(`备用找到: text="${text}"`);
                        result.found = true;
                        result.buttonText = text;
                        btn.click();
                        result.clicked = true;
                        return result;
                    }
                }
            }
            
            return result;
        }''')
        
        if js_result.get('debug'):
            for debug_msg in js_result['debug']:
                douyin_logger.info(f"  [JS Debug] {debug_msg}")
        
        clicked = js_result.get('clicked', False)
        if clicked:
            douyin_logger.success(f"  [+] JavaScript 成功点击按钮: '{js_result.get('buttonText', '')}'")
            return
        
        # ========== 策略4: 键盘模拟兜底 ==========
        douyin_logger.info("  [-] 所有方案失败，尝试模拟 Tab + Enter 键...")
        try:
            await page.keyboard.press('Tab')
            await asyncio.sleep(0.2)
            await page.keyboard.press('Enter')
            douyin_logger.info("  [+] 已模拟 Tab + Enter 键")
        except Exception as key_e:
            douyin_logger.warning(f"  [!] 键盘模拟失败: {key_e}")
        
        douyin_logger.warning("  [!] 未能自动点击验证按钮，请手动点击")





    async def set_location(self, page: Page, location: str = ""):
        if not location:
            return
        # todo supoort location later
        # await page.get_by_text('添加标签').locator("..").locator("..").locator("xpath=following-sibling::div").locator(
        #     "div.semi-select-single").nth(0).click()
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def handle_product_dialog(self, page: Page, product_title: str):
        """处理商品编辑弹窗"""

        await page.wait_for_timeout(2000)
        await page.wait_for_selector('input[placeholder="请输入商品短标题"]', timeout=10000)
        short_title_input = page.locator('input[placeholder="请输入商品短标题"]')
        if not await short_title_input.count():
            douyin_logger.error("[-] 未找到商品短标题输入框")
            return False
        product_title = product_title[:10]
        await short_title_input.fill(product_title)
        # 等待一下让界面响应
        await page.wait_for_timeout(1000)

        finish_button = page.locator('button:has-text("完成编辑")')
        if 'disabled' not in await finish_button.get_attribute('class'):
            await finish_button.click()
            douyin_logger.debug("[+] 成功点击'完成编辑'按钮")
            
            # 等待对话框关闭
            await page.wait_for_selector('.semi-modal-content', state='hidden', timeout=5000)
            return True
        else:
            douyin_logger.error("[-] '完成编辑'按钮处于禁用状态，尝试直接关闭对话框")
            # 如果按钮禁用，尝试点击取消或关闭按钮
            cancel_button = page.locator('button:has-text("取消")')
            if await cancel_button.count():
                await cancel_button.click()
            else:
                # 点击右上角的关闭按钮
                close_button = page.locator('.semi-modal-close')
                await close_button.click()
            
            await page.wait_for_selector('.semi-modal-content', state='hidden', timeout=5000)
            return False
        
    async def main(self):
        """带超时控制的主入口，总超时180秒（3分钟）"""
        RPA_TIMEOUT_SECONDS = 180
        
        try:
            await asyncio.wait_for(self.upload(), timeout=RPA_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            error_msg = f"RPA发布超时: 执行时间超过 {RPA_TIMEOUT_SECONDS} 秒"
            douyin_logger.error(f"  [-] {error_msg}")
            await self.update_status(0, error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            douyin_logger.error(f"  [-] RPA发布失败: {error_msg}")
            await self.update_status(0, error_msg)
            raise
