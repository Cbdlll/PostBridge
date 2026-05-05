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
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
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
        kuaishou_logger.warning(f"human_scroll 失败: {e}")


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
        kuaishou_logger.warning(f"human_click 失败，回退普通点击: {e}")
        try:
            await locator.click(timeout=timeout)
        except:
            pass


async def dismiss_guide_overlay(page: Page):
    """
    关闭快手创作服务平台的引导弹窗/遮罩层 (react-joyride)
    使用纯 Playwright 原生 API，不使用 JS evaluate
    """
    try:
        # 1. 尝试点击引导弹窗的按钮 (下一步 / 跳过 / 我知道了 / 完成)
        guide_buttons = [
            'button:has-text("下一步")',
            'button:has-text("跳过")',
            'button:has-text("我知道了")',
            'button:has-text("完成")',
            'button:has-text("知道了")',
            '[class*="joyride"] button',
            '[aria-label="Close"]', 
            '[aria-label="关闭"]',
            # 扩展选择器：常见关闭按钮
            '.close-btn',
            '[class*="close"]',
            'button.ant-modal-close',
        ]
        
        for selector in guide_buttons:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click(force=True)  # 使用 force=True 强制点击
                    kuaishou_logger.info(f"  [+] 已关闭引导弹窗: {selector}")
                    await asyncio.sleep(0.5)
                    return True
            except:
                pass
        
        # 2. 尝试按下 ESC 键关闭可能存在的弹窗
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        
        # 3. 再次尝试 ESC（某些弹窗需要两次）
        await page.keyboard.press("Escape")
        
        return False
        
    except Exception as e:
        kuaishou_logger.warning(f"dismiss_guide_overlay 失败: {e}")
        return False



class KSVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, profile_dir, description='', task_id=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.profile_dir = profile_dir  # UserDataDir 路径
        self.description = description  # 视频描述/简介
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.task_id = task_id  # 任务ID，用于前端通知

    async def handle_upload_error(self, page):
        kuaishou_logger.error("视频出错了，重新上传中")
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def save_failure_screenshot(self, page, error_msg: str) -> str:
        """保存失败时的页面截图到 rpa_failed_log 目录"""
        try:
            from pathlib import Path
            from conf import BASE_DIR
            
            screenshot_dir = Path(BASE_DIR / "data" / "rpa_failed_screenshots" / "kuaishou")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            task_id_safe = self.task_id.replace('/', '_') if self.task_id else 'unknown'
            filename = f"ks_{task_id_safe}_{timestamp}.png"
            filepath = screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            kuaishou_logger.info(f"  [✓] 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            kuaishou_logger.warning(f"保存失败截图失败: {e}")
            return ""

    async def upload(self) -> None:
        """上传视频到快手（使用 UserDataDir 持久化浏览器）"""
        context = None
        page = None  # 用于失败截图
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
                await setup_resource_blocking(page, block_images=False, block_fonts=False, block_analytics=True)
                
                # 导航重试机制
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        kuaishou_logger.info(f'[-] 正在跳转发布页面 (Attempt {attempt + 1}/{max_nav_retries})...')
                        await page.goto("https://cp.kuaishou.com/article/publish/video", timeout=45000)
                        await page.wait_for_url("https://cp.kuaishou.com/article/publish/video", timeout=30000)
                        break
                    except Exception as e:
                        kuaishou_logger.warning(f"[-] 导航超时或失败: {e}")
                        if attempt == max_nav_retries - 1:
                            kuaishou_logger.error("[-] 导航最终失败，放弃本次任务")
                            raise e
                        await random_delay(2, 4)
                
                kuaishou_logger.info('正在上传-------{}.mp4'.format(self.title))
                await random_delay(0.5, 1.0)
                
                # 关闭引导弹窗
                await dismiss_guide_overlay(page)
                
                # 点击 "上传视频" 按钮
                upload_button = page.locator("button[class^='_upload-btn']")
                await upload_button.wait_for(state='visible')
                await random_delay(0.3, 0.6)
                
                async with page.expect_file_chooser() as fc_info:
                    await human_click(page, upload_button)
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.file_path)
                
                await random_delay(1.5, 2.5)
                
                # 再次尝试关闭引导弹窗（上传后可能出现新的引导）
                await dismiss_guide_overlay(page)
                await random_delay(0.5, 1.0)
                
                # 等待按钮可交互（"我知道了"弹窗）
                new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
                if await new_feature_button.count() > 0:
                    await new_feature_button.click()
                    await random_delay(0.3, 0.5)
                
                # 关闭引导弹窗
                await dismiss_guide_overlay(page)
                
                kuaishou_logger.info("正在填充标题和话题...")
                
                # 点击描述输入框之前再次检查并关闭引导遮罩
                await dismiss_guide_overlay(page)
                
                desc_locator = page.get_by_text("描述").locator("xpath=following-sibling::div")
                await human_click(page, desc_locator)
                
                kuaishou_logger.info("clear existing title")
                # 使用多次 Backspace 清除内容，避免 Ctrl+A 选中整个页面
                for _ in range(50):
                    await page.keyboard.press("Backspace")
                await random_delay(0.2, 0.4)
                
                kuaishou_logger.info("filling new title")
                await page.keyboard.type(self.title)
                await page.keyboard.press("Enter")
                await random_delay(0.3, 0.6)
                
                # 填充描述/简介（如果有）
                if self.description:
                    kuaishou_logger.info("filling description")
                    await page.keyboard.type(self.description)
                    await page.keyboard.press("Enter")
                    await random_delay(0.3, 0.6)
                
                # 快手只能添加3个话题
                # 先关闭可能存在的引导弹窗覆盖层
                await dismiss_guide_overlay(page)
                
                for index, tag in enumerate(self.tags[:3], start=1):
                    kuaishou_logger.info(f"正在添加第{index}个话题: #{tag}")
                    # 点击 "#话题" 按钮来触发话题输入模式
                    topic_btn = page.locator('text="#话题"')
                    if await topic_btn.count() > 0:
                        await topic_btn.click()
                        await random_delay(0.3, 0.5)
                    
                    # 输入标签内容
                    await page.keyboard.type(tag)
                    await random_delay(1.2, 1.8)  # 等待下拉建议列表加载
                    
                    # 尝试点击下拉列表第一项（如果存在）
                    suggestion_selectors = [
                        'div[class*="topic-item"]',
                        'div[class*="suggestion"] >> nth=0',
                        'li[class*="topic"]',
                        'div[class*="dropdown"] div >> nth=0',
                    ]
                    
                    suggestion_clicked = False
                    for sel in suggestion_selectors:
                        try:
                            suggestion = page.locator(sel).first
                            if await suggestion.count() > 0 and await suggestion.is_visible():
                                await suggestion.click()
                                kuaishou_logger.info(f"  [✓] 已选择话题建议: {tag}")
                                suggestion_clicked = True
                                break
                        except:
                            pass
                    
                    # 如果没有找到下拉项，按 Enter 确认（避免用 Space 导致空格被插入文字）
                    if not suggestion_clicked:
                        await page.keyboard.press("Enter")
                        kuaishou_logger.info(f"  [✓] 已按 Enter 确认话题: {tag}")
                    
                    await random_delay(0.5, 0.8)
                
                # 等待视频上传完成
                max_retries = 60
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        number = await page.locator("text=上传中").count()
                        
                        if number == 0:
                            kuaishou_logger.success("视频上传完毕")
                            break
                        else:
                            if retry_count % 5 == 0:
                                kuaishou_logger.info("正在上传视频中...")
                            await random_delay(1.5, 2.5)
                    except Exception as e:
                        kuaishou_logger.error(f"检查上传状态时发生错误: {e}")
                        await random_delay(1.5, 2.5)
                    retry_count += 1
                
                if retry_count == max_retries:
                    kuaishou_logger.warning("超过最大重试次数，视频上传可能未完成。")
                
                # 定时任务
                if self.publish_date != 0:
                    await self.set_schedule_time(page, self.publish_date)
                
                # 发布流程
                kuaishou_logger.info("开始发布流程 (优化版)...")
                max_publish_attempts = 30
                publish_success = False
                
                for attempt in range(max_publish_attempts):
                    try:
                        # 关闭引导弹窗 (如果存在)
                        await dismiss_guide_overlay(page)
                        
                        # 1. 点击发布按钮 (使用 exact=True 精确匹配)
                        publish_btn = page.get_by_text("发布", exact=True)
                        if await publish_btn.count() > 0 and await publish_btn.is_visible():
                            await publish_btn.click()
                            kuaishou_logger.info(f"  [发布] 点击 '发布' ({attempt + 1})")
                            await asyncio.sleep(1)

                        # 2. 点击确认发布
                        confirm_btn = page.get_by_text("确认发布")
                        if await confirm_btn.count() > 0 and await confirm_btn.is_visible():
                            await confirm_btn.click()
                            kuaishou_logger.info("  [发布] 点击 '确认发布'")
                            await asyncio.sleep(1)

                        # 3. 验证成功 (URL跳转 或 文本提示)
                        try:
                            if "status=2" in page.url and "from=publish" in page.url:
                                publish_success = True
                            else:
                                # 尝试等待URL变化 (最多等待 2 秒)
                                await page.wait_for_url(
                                    "https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
                                    timeout=2000
                                )
                                publish_success = True
                        except:
                            pass
                        
                        if not publish_success:
                            success_indicators = ['发布成功', '上传成功', '已发布']
                            for text in success_indicators:
                                if await page.get_by_text(text).count() > 0:
                                    publish_success = True
                                    break
                                    
                        if publish_success:
                            kuaishou_logger.success("视频发布成功！")
                            break
                            
                        # 检测验证码
                        if await self.check_verification_code(page):
                            kuaishou_logger.warning("检测到验证码，等待人工处理...")
                            await asyncio.sleep(5)
                            
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        kuaishou_logger.info(f"发布检测中: {e}")
                        await asyncio.sleep(1)

                if not publish_success:
                    kuaishou_logger.warning("超过最大重试次数，发布状态未确认，请手动检查")
                
                # UserDataDir 模式下，登录态自动保存，无需手动保存 cookie
                kuaishou_logger.info('发布完成，用户配置已自动保存！')
                
        except RuntimeError as e:
            kuaishou_logger.error(f"  [-] 账号目录被占用: {e}")
            raise
        except Exception as e:
            # 保存失败截图
            if page:
                await self.save_failure_screenshot(page, str(e))
            raise
        finally:
            await random_delay(0.3, 0.5)
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

    async def check_verification_code(self, page):
        """
        检测页面是否出现验证码弹窗
        返回 True 表示需要验证码，False 表示不需要
        """
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
                    kuaishou_logger.warning(f"检测到验证提示: {text}")
                    return True
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
                kuaishou_logger.warning(f"检测到验证iframe: {selector}")
                return True
        
        return False

    async def main(self):
        """带超时控制的主入口，总超时180秒（3分钟）"""
        RPA_TIMEOUT_SECONDS = 180
        
        try:
            await asyncio.wait_for(self.upload(), timeout=RPA_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            error_msg = f"RPA发布超时: 执行时间超过 {RPA_TIMEOUT_SECONDS} 秒"
            kuaishou_logger.error(f"  [-] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            kuaishou_logger.error(f"  [-] RPA发布失败: {error_msg}")
            raise

    async def set_schedule_time(self, page, publish_date):
        kuaishou_logger.info("click schedule")
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M:%S")
        await page.locator("label:text('发布时间')").locator('xpath=following-sibling::div').locator(
            '.ant-radio-input').nth(1).click()
        await random_delay(0.5, 1.0)

        await page.locator('div.ant-picker-input input[placeholder="选择日期时间"]').click()
        await random_delay(0.3, 0.5)

        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await random_delay(0.5, 1.0)
