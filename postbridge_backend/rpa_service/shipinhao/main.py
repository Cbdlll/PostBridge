# -*- coding: utf-8 -*-
"""
视频号 (微信视频号) 视频上传 RPA 脚本
参照抖音/小红书/快手脚本实现，使用 Playwright 自动化操作
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
from utils.log import tencent_logger
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
        tencent_logger.warning(f"human_scroll 失败: {e}")


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
        tencent_logger.warning(f"human_click 失败，回退普通点击: {e}")
        try:
            await locator.click(timeout=timeout)
        except:
            pass


# ========================================
# 以下旧的 Cookie 相关函数已废弃
# 新架构使用 UserDataDir，无需这些函数
# ========================================

async def weixin_setup(*args, **kwargs):
    """废弃函数存根，保持旧版CLI兼容性"""
    tencent_logger.warning("[废弃] weixin_setup 已废弃，新架构使用 auth.py 进行 cookie 验证")
    return True


def format_str_for_short_title(origin_title: str) -> str:
    # 定义允许的特殊字符
    allowed_special_chars = "《》“”:+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else ' ' if char == ',' else '' for
                      char in origin_title]
    formatted_string = ''.join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += ' ' * (6 - len(formatted_string))

    return formatted_string



class TencentVideo(object):
    """视频号视频上传类"""
    
    def __init__(self, title, file_path, tags, publish_date: datetime, profile_dir, category=None, is_draft=False, task_id=None, description=''):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.profile_dir = profile_dir  # UserDataDir 路径
        self.category = category
        self.headless = LOCAL_CHROME_HEADLESS
        self.is_draft = is_draft  # 是否保存为草稿
        self.local_executable_path = LOCAL_CHROME_PATH
        self.task_id = task_id  # 任务ID，用于前端通知
        self.description = description  # 视频简介

    async def save_failure_screenshot(self, page, error_msg: str) -> str:
        """保存失败时的页面截图到 data/rpa_failed_screenshots/shipinhao/ 目录"""
        try:
            from pathlib import Path
            from conf import BASE_DIR
            
            screenshot_dir = Path(BASE_DIR / "data" / "rpa_failed_screenshots" / "shipinhao")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"shipinhao_{timestamp}.png"
            filepath = screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            tencent_logger.info(f"  [✓] 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            tencent_logger.warning(f"保存失败截图失败: {e}")
            return ""

    async def set_schedule_time_tencent(self, page, publish_date):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = str(publish_date.month) if publish_date.month > 9 else "0" + str(publish_date.month)
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click('button.weui-desktop-btn__icon__right')

        # 获取页面元素
        elements = await page.query_selector_all('table.weui-desktop-picker__table a')

        # 遍历元素并点击匹配的元素
        for element in elements:
            if 'weui-desktop-picker__disabled' in await element.evaluate('el => el.className'):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 输入小时部分（假设选择11小时）
        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date.hour))

        # 选择标题栏（令定时时间生效）
        await page.locator("div.input-editor").click()

    async def handle_upload_error(self, page):
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)

    async def upload(self) -> None:
        """上传视频到视频号（使用 UserDataDir 持久化浏览器）"""
        context = None
        page = None
        profile_lock = None
        playwright = None
        
        try:
            # 使用 ProfileLock 确保同一账号不会同时操作
            profile_lock = ProfileLock(Path(self.profile_dir))
            async with profile_lock:
                # 视频号专用：简化的浏览器启动，与 openBrowser 保持一致
                # 只保留反自动化指纹，不添加任何可能影响资源加载的参数
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                
                # 最简化的启动参数：仅反自动化检测
                minimal_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--disable-infobars',
                    '--lang=zh-CN',
                ]
                
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=self.headless,
                    executable_path=self.local_executable_path if self.local_executable_path else None,
                    args=minimal_args,
                    ignore_default_args=['--enable-automation'],
                    viewport={'width': 1280, 'height': 800},
                )
                tencent_logger.info('[+] 浏览器上下文已创建')
                
                # 视频号专用：简化版反检测脚本
                # 不使用完整的 stealth.min.js（与视频号页面冲突）
                # 只注入核心的 navigator.webdriver 隐藏
                await context.add_init_script("""
                    (function() {
                        // 核心：隐藏 navigator.webdriver
                        try {
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined,
                                configurable: true
                            });
                        } catch(e) {}
                        
                        // 隐藏 Chrome Driver 痕迹
                        try {
                            for (let prop in window) {
                                if (prop.match(/^cdc_|^__webdriver_|^_Selenium_/i)) {
                                    try { delete window[prop]; } catch(e) {}
                                }
                            }
                        } catch(e) {}
                    })();
                """)
                tencent_logger.info('[+] 已注入简化版反检测脚本')
                
                # 获取或创建页面
                page = context.pages[0] if context.pages else await context.new_page()
                tencent_logger.info(f'[+] 页面已创建')
                
                # 视频号页面不进行任何资源拦截
                
                # 导航重试机制
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        tencent_logger.info(f'[-] 正在跳转发布页面 (Attempt {attempt + 1}/{max_nav_retries})...')
                        await page.goto("https://channels.weixin.qq.com/platform/post/create", timeout=90000)  # 90秒超时
                        await random_delay(3, 5)  # 视频号页面加载较慢，多等一会
                        break
                    except Exception as e:
                        tencent_logger.warning(f"[-] 导航超时或失败: {e}")
                        if attempt == max_nav_retries - 1:
                            raise e
                        await random_delay(3, 5)
                
                tencent_logger.info(f'[+] 正在上传视频: {self.title}')
                await random_delay(1, 2)
                
                # 等待文件上传输入框可见（视频号页面加载较慢）
                tencent_logger.info('[-] 等待文件上传输入框...')
                file_input = page.locator('input[type="file"]')
                await file_input.wait_for(state="attached", timeout=90000)  # 90秒超时
                await file_input.set_input_files(self.file_path)
                
                # 填充标题和话题
                await self.add_title_tags(page)
                # 合集功能
                await self.add_collection(page)
                # 原创选择
                await self.add_original(page)
                # 检测上传状态
                await self.detect_upload_status(page)
                
                if self.publish_date != 0:
                    await self.set_schedule_time_tencent(page, self.publish_date)
                
                # 添加短标题
                await self.add_short_title(page)
                
                await self.click_publish(page)
                
                # UserDataDir 模式下，登录态自动保存，无需手动保存 cookie
                tencent_logger.success('  [-] 发布完成，用户配置已自动保存！')
                await random_delay(0.3, 0.5)
                
        except RuntimeError as e:
            tencent_logger.error(f"  [-] 账号目录被占用: {e}")
            raise
        except Exception as e:
            # 保存失败截图
            if page:
                await self.save_failure_screenshot(page, str(e))
            raise
        finally:
            # 关闭浏览器上下文
            if context:
                try:
                    await context.close()
                except:
                    pass
            
            # 关闭 playwright 实例
            if playwright:
                try:
                    await playwright.stop()
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

    async def add_short_title(self, page):
        short_title_element = page.get_by_text("短标题", exact=True).locator("..").locator(
            "xpath=following-sibling::div").locator(
            'span input[type="text"]')
        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)

    async def click_publish(self, page):
        while True:
            try:
                if self.is_draft:
                    # 点击"保存草稿"按钮
                    draft_button = page.locator('div.form-btns button:has-text("保存草稿")')
                    if await draft_button.count():
                        await draft_button.click()
                    # 等待跳转到草稿箱页面或确认保存成功
                    await page.wait_for_url("**/post/list**", timeout=5000)  # 使用通配符匹配包含post/list的URL
                    tencent_logger.success("  [-]视频草稿保存成功")
                else:
                    # 点击"发表"按钮
                    publish_button = page.locator('div.form-btns button:has-text("发表")')
                    if await publish_button.count():
                        await publish_button.click()
                    await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=5000)
                    tencent_logger.success("  [-]视频发布成功")
                break
            except Exception as e:
                current_url = page.url
                if self.is_draft:
                    # 检查是否在草稿相关的页面
                    if "post/list" in current_url or "draft" in current_url:
                        tencent_logger.success("  [-]视频草稿保存成功")
                        break
                else:
                    # 检查是否在发布列表页面
                    if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                        tencent_logger.success("  [-]视频发布成功")
                        break
                tencent_logger.exception(f"  [-] Exception: {e}")
                tencent_logger.info("  [-] 视频正在发布中...")
                await asyncio.sleep(0.5)

    async def detect_upload_status(self, page):
        while True:
            # 匹配删除按钮，代表视频上传完毕，如果不存在，代表视频正在上传，则等待
            try:
                # 匹配删除按钮，代表视频上传完毕
                if "weui-desktop-btn_disabled" not in await page.get_by_role("button", name="发表").get_attribute(
                        'class'):
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    tencent_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    # 出错了视频出错
                    if await page.locator('div.status-msg.error').count() and await page.locator(
                            'div.media-status-content div.tag-inner:has-text("删除")').count():
                        tencent_logger.error("  [-] 发现上传出错了...准备重试")
                        await self.handle_upload_error(page)
            except:
                tencent_logger.info("  [-] 正在上传视频中...")
                await asyncio.sleep(2)

    async def add_title_tags(self, page):
        """视频号发布页面没有单独标题输入框，将标题、简介和标签一起输入到内容编辑区"""
        await page.locator("div.input-editor").click()
        await random_delay(0.3, 0.5)
        
        # 输入标题
        await page.keyboard.type(self.title)
        
        # 如果有简介，换行后输入简介
        if self.description:
            await page.keyboard.press("Enter")
            await random_delay(0.2, 0.4)
            await page.keyboard.type(self.description)
        
        # 换行后输入标签
        await page.keyboard.press("Enter")
        await random_delay(0.2, 0.4)
        
        for index, tag in enumerate(self.tags, start=1):
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
            await random_delay(0.1, 0.3)
        
        tencent_logger.info(f"成功添加hashtag: {len(self.tags)}")

    async def add_collection(self, page):
        collection_elements = page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
            '.option-list-wrap > div')
        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await collection_elements.first.click()

    async def add_original(self, page):
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()
        # 检查 "我已阅读并同意 《视频号原创声明使用条款》" 元素是否存在
        label_locator = await page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
        # 2023年11月20日 wechat更新: 可能新账号或者改版账号，出现新的选择页面
        if await page.locator('div.label span:has-text("声明原创")').count() and self.category:
            # 因处罚无法勾选原创，故先判断是否可用
            if not await page.locator('div.declare-original-checkbox input.ant-checkbox-input').is_disabled():
                await page.locator('div.declare-original-checkbox input.ant-checkbox-input').click()
                if not await page.locator(
                        'div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible').count():
                    await page.locator('div.declare-original-dialog input.ant-checkbox-input:visible').click()
            if await page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible').count():
                await page.locator('div.form-content:visible').click()  # 下拉菜单
                await page.locator(
                    f'div.form-content:visible ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele:has-text("{self.category}")').first.click()
                await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("声明原创"):visible').count():
                await page.locator('button:has-text("声明原创"):visible').click()

    async def main(self):
        """带超时控制的主入口，总超时480秒（8分钟）- 视频号页面加载较慢"""
        RPA_TIMEOUT_SECONDS = 480
        
        try:
            await asyncio.wait_for(self.upload(), timeout=RPA_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            error_msg = f"RPA发布超时: 执行时间超过 {RPA_TIMEOUT_SECONDS} 秒"
            tencent_logger.error(f"  [-] {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = str(e)
            tencent_logger.error(f"  [-] RPA发布失败: {error_msg}")
            raise
