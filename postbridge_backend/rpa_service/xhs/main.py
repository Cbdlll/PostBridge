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
from utils.log import xiaohongshu_logger
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
        xiaohongshu_logger.warning(f"human_scroll 失败: {e}")


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
        xiaohongshu_logger.warning(f"human_click 失败，回退普通点击: {e}")
        try:
            await locator.click(timeout=timeout)
        except:
            pass


# ========================================
# 以下旧的 Cookie 相关函数已废弃
# 新架构使用 UserDataDir，无需这些函数
# ========================================



class XiaoHongShuVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, profile_dir, thumbnail_path=None, description='', task_id=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.profile_dir = profile_dir  # UserDataDir 路径
        self.description = description  # 视频简介/正文内容
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path
        self.task_id = task_id

    async def set_schedule_time_xiaohongshu(self, page, publish_date):
        print("  [-] 正在设置定时发布时间...")
        print(f"publish_date: {publish_date}")

        # 使用文本内容定位元素
        # element = await page.wait_for_selector(
        #     'label:has-text("定时发布")',
        #     timeout=5000  # 5秒超时时间
        # )
        # await element.click()

        # # 选择包含特定文本内容的 label 元素
        label_element = page.locator("label:has-text('定时发布')")
        # # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        print(f"publish_date_hour: {publish_date_hour}")

        await asyncio.sleep(1)
        await page.locator('.el-input__inner[placeholder="选择日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def save_failure_screenshot(self, page, error_msg: str) -> str:
        """保存失败时的页面截图到 data/rpa_failed_screenshots/xhs/ 目录"""
        try:
            from pathlib import Path
            from conf import BASE_DIR
            
            screenshot_dir = Path(BASE_DIR / "data" / "rpa_failed_screenshots" / "xhs")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"xhs_{timestamp}.png"
            filepath = screenshot_dir / filename
            
            await page.screenshot(path=str(filepath), full_page=True)
            xiaohongshu_logger.info(f"  [✓] 失败截图已保存: {filepath}")
            return str(filepath)
        except Exception as e:
            xiaohongshu_logger.warning(f"保存失败截图失败: {e}")
            return ""

    async def upload(self) -> None:
        """上传视频到小红书（使用 UserDataDir 持久化浏览器）"""
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
                await setup_resource_blocking(page, block_images=False, block_fonts=True, block_analytics=True)
            
                # 导航重试机制
                max_nav_retries = 3
                for attempt in range(max_nav_retries):
                    try:
                        xiaohongshu_logger.info(f'[-] 正在跳转发布页面 (Attempt {attempt + 1}/{max_nav_retries})...')
                        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video", timeout=45000)
                        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video", timeout=30000)
                        break
                    except Exception as e:
                        xiaohongshu_logger.warning(f"[-] 导航超时或失败: {e}")
                        if attempt == max_nav_retries - 1:
                            xiaohongshu_logger.error("[-] 导航最终失败，放弃本次任务")
                            raise e
                        await random_delay(2, 4)
                
                xiaohongshu_logger.info(f'[+]正在上传-------{self.title}.mp4')
                await random_delay(0.5, 1.0)
                
                # 点击 "上传视频" 按钮
                await page.locator("div[class^='upload-content'] input[class='upload-input']").set_input_files(self.file_path)

                # 等待上传完成
                while True:
                    try:
                        # 等待upload-input元素出现
                        upload_input = await page.wait_for_selector('input.upload-input', timeout=3000)
                        # 获取下一个兄弟元素
                        preview_new = await upload_input.query_selector(
                            'xpath=following-sibling::div[contains(@class, "preview-new")]')
                        if preview_new:
                            # 在preview-new元素中查找包含"上传成功"的stage元素
                            stage_elements = await preview_new.query_selector_all('div.stage')
                            upload_success = False
                            for stage in stage_elements:
                                text_content = await stage.inner_text()
                                if '上传成功' in text_content:
                                    upload_success = True
                                    break
                            if upload_success:
                                xiaohongshu_logger.info("[+] 检测到上传成功标识!")
                                break  # 成功检测到上传成功后跳出循环
                            else:
                                xiaohongshu_logger.info("  [-] 未找到上传成功标识，继续等待...")
                        else:
                            xiaohongshu_logger.info("  [-] 未找到预览元素，继续等待...")
                            await random_delay(0.8, 1.2)
                    except Exception as e:
                        xiaohongshu_logger.info(f"  [-] 检测过程出错: {str(e)}，重新尝试...")
                        await random_delay(0.3, 0.6)

                # 填充标题和话题
                await random_delay(0.8, 1.2)
                xiaohongshu_logger.info(f'  [-] 正在填充标题和话题...')
                
                # 1. 填充标题（多种选择器备选）
                title_filled = False
                title_selectors = [
                    ('div.plugin.title-container input.d-text', 'fill'),  # 新版标题输入框
                    ('input[placeholder*="标题"]', 'fill'),  # 通过 placeholder 匹配
                    ('.c-input_inner[maxlength]', 'fill'),  # 另一种输入框
                ]
                
                for selector, method in title_selectors:
                    try:
                        title_input = page.locator(selector).first
                        if await title_input.count() > 0 and await title_input.is_visible():
                            await title_input.fill(self.title[:30])
                            xiaohongshu_logger.success(f'  [+] 标题已填充: {self.title[:30]}')
                            title_filled = True
                            break
                    except Exception as e:
                        continue
                
                # 备选方案：使用 .notranslate 区域键盘输入
                if not title_filled:
                    try:
                        titlecontainer = page.locator(".notranslate").first
                        if await titlecontainer.count() > 0:
                            await human_click(page, titlecontainer)
                            await random_delay(0.2, 0.4)
                            await page.keyboard.press("Control+KeyA")
                            await page.keyboard.press("Delete")
                            await page.keyboard.type(self.title[:30])
                            await page.keyboard.press("Enter")
                            xiaohongshu_logger.success(f'  [+] 标题已填充(备选): {self.title[:30]}')
                            title_filled = True
                    except Exception as e:
                        xiaohongshu_logger.warning(f'  [!] 标题填充备选方案失败: {e}')
                
                if not title_filled:
                    xiaohongshu_logger.warning('  [!] 未找到标题输入框')
                
                await random_delay(0.5, 0.8)
                
                # 2. 填充简介和话题标签（在同一个正文输入框）
                xiaohongshu_logger.info(f'  [-] 正在填充简介和话题...')
                
                # 定位正文内容输入区域
                content_selectors = [
                    '.ql-editor',  # Quill 编辑器
                    'div[contenteditable="true"]',  # 可编辑区域
                    '[data-placeholder*="正文"]',  # 带 placeholder 的区域
                ]
                
                content_filled = False
                for selector in content_selectors:
                    try:
                        content_area = page.locator(selector).first
                        if await content_area.count() > 0 and await content_area.is_visible():
                            # 点击进入正文输入区域
                            await human_click(page, content_area, timeout=3000)
                            await random_delay(0.3, 0.5)
                            
                            # 2.1 填充简介（如果有）
                            if self.description:
                                xiaohongshu_logger.info(f'  [-] 正在输入简介...')
                                await page.keyboard.type(self.description)
                                xiaohongshu_logger.success(f'  [+] 简介已填充: {self.description[:20]}...')
                                await random_delay(0.3, 0.5)
                                # 简介输入完成后按回车换行
                                await page.keyboard.press("Enter")
                                await random_delay(0.3, 0.5)
                            
                            # 2.2 填充话题标签
                            xiaohongshu_logger.info(f'  [-] 正在填充话题标签...')
                            for index, tag in enumerate(self.tags, start=1):
                                # 输入话题
                                await page.keyboard.type("#" + tag)
                                xiaohongshu_logger.info(f'  [-] 输入话题 #{tag}，等待下拉列表...')
                                
                                # 等待话题下拉建议列表出现
                                try:
                                    # 等待下拉列表加载
                                    await page.wait_for_selector('div[class*="topic"] >> text=/.*浏览/', timeout=2000)
                                    await random_delay(0.3, 0.5)
                                except:
                                    # 备选：等待固定时间
                                    await random_delay(1.2, 1.8)
                                
                                # 按回车确认选择第一个话题
                                await page.keyboard.press("Enter")
                                await random_delay(0.5, 0.8)
                            
                            xiaohongshu_logger.info(f'  [+] 总共添加{len(self.tags)}个话题')
                            content_filled = True
                            break
                    except Exception as e:
                        xiaohongshu_logger.info(f'  [-] 选择器 {selector} 失败: {e}')
                        continue
                
                if not content_filled:
                    xiaohongshu_logger.warning('  [!] 无法找到正文输入区域，尝试直接在页面输入')
                    # 兜底：直接键盘输入
                    try:
                        if self.description:
                            await page.keyboard.type(self.description)
                            await page.keyboard.press("Enter")
                            await random_delay(0.3, 0.5)
                        
                        for tag in self.tags:
                            await page.keyboard.type("#" + tag)
                            await random_delay(1.2, 1.8)
                            await page.keyboard.press("Enter")
                            await random_delay(0.5, 0.8)
                        xiaohongshu_logger.info(f'  [+] 内容已填充(兜底方案)')
                    except Exception as e:
                        xiaohongshu_logger.error(f'  [-] 内容填充最终失败: {e}')

                # 定时发布设置
                if self.publish_date != 0:
                    await self.set_schedule_time_xiaohongshu(page, self.publish_date)

                # 判断视频是否发布成功
                max_publish_attempts = 20
                for attempt in range(max_publish_attempts):
                    try:
                        # 等待包含"定时发布"或"发布"文本的button元素出现并点击
                        if self.publish_date != 0:
                            publish_btn = page.locator('button:has-text("定时发布")')
                        else:
                            publish_btn = page.locator('button:has-text("发布")')
                        
                        if await publish_btn.count() > 0:
                            await human_click(page, publish_btn)
                        
                        await page.wait_for_url(
                            "https://creator.xiaohongshu.com/publish/success?**",
                            timeout=3000
                        )  # 如果自动跳转到作品页面，则代表发布成功
                        xiaohongshu_logger.success("  [-]视频发布成功")
                        break
                    except:
                        xiaohongshu_logger.info(f"  [-] 视频正在发布中... ({attempt + 1}/{max_publish_attempts})")
                        await random_delay(0.3, 0.6)

                # UserDataDir 模式下，登录态自动保存，无需手动保存 cookie
                xiaohongshu_logger.success('  [-] 发布完成，用户配置已自动保存！')
                await random_delay(0.3, 0.5)
                
        except RuntimeError as e:
            xiaohongshu_logger.error(f"  [-] 账号目录被占用: {e}")
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
            
            # 强制释放锁
            if profile_lock:
                try:
                    profile_lock.force_release()
                except:
                    pass
            
            # 清理 profile 目录锁文件
            ProfileLock.cleanup_profile(Path(self.profile_dir))
    
    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="设置竖封面"')
            await page.wait_for_timeout(2000)  # 等待2秒
            # 定位到上传区域并点击
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)  # 等待2秒
            await page.locator("div[class^='extractFooter'] button:visible:has-text('完成')").click()
            # finish_confirm_element = page.locator("div[class^='confirmBtn'] >> div:has-text('完成')")
            # if await finish_confirm_element.count():
            #     await finish_confirm_element.click()
            # await page.locator("div[class^='footer'] button:has-text('完成')").click()

    async def set_location(self, page: Page, location: str = "青岛市"):
        print(f"开始设置位置: {location}")
        
        # 点击地点输入框
        print("等待地点输入框加载...")
        loc_ele = await page.wait_for_selector('div.d-text.d-select-placeholder.d-text-ellipsis.d-text-nowrap')
        print(f"已定位到地点输入框: {loc_ele}")
        await loc_ele.click()
        print("点击地点输入框完成")
        
        # 输入位置名称
        print(f"等待1秒后输入位置名称: {location}")
        await page.wait_for_timeout(1000)
        await page.keyboard.type(location)
        print(f"位置名称输入完成: {location}")
        
        # 等待下拉列表加载
        print("等待下拉列表加载...")
        dropdown_selector = 'div.d-popover.d-popover-default.d-dropdown.--size-min-width-large'
        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_selector(dropdown_selector, timeout=3000)
            print("下拉列表已加载")
        except:
            print("下拉列表未按预期显示，可能结构已变化")
        
        # 增加等待时间以确保内容加载完成
        print("额外等待1秒确保内容渲染完成...")
        await page.wait_for_timeout(1000)
        
        # 尝试更灵活的XPath选择器
        print("尝试使用更灵活的XPath选择器...")
        flexible_xpath = (
            f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
            f'//div[contains(@class, "d-options-wrapper")]'
            f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
            f'//div[contains(@class, "name") and text()="{location}"]'
        )
        await page.wait_for_timeout(3000)
        
        # 尝试定位元素
        print(f"尝试定位包含'{location}'的选项...")
        try:
            # 先尝试使用更灵活的选择器
            location_option = await page.wait_for_selector(
                flexible_xpath,
                timeout=3000
            )
            
            if location_option:
                print(f"使用灵活选择器定位成功: {location_option}")
            else:
                # 如果灵活选择器失败，再尝试原选择器
                print("灵活选择器未找到元素，尝试原始选择器...")
                location_option = await page.wait_for_selector(
                    f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    f'//div[contains(@class, "d-options-wrapper")]'
                    f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    f'/div[1]//div[contains(@class, "name") and text()="{location}"]',
                    timeout=2000
                )
            
            # 滚动到元素并点击
            print("滚动到目标选项...")
            await location_option.scroll_into_view_if_needed()
            print("元素已滚动到视图内")
            
            # 增加元素可见性检查
            is_visible = await location_option.is_visible()
            print(f"目标选项是否可见: {is_visible}")
            
            # 点击元素
            print("准备点击目标选项...")
            await location_option.click()
            print(f"成功选择位置: {location}")
            return True
            
        except Exception as e:
            print(f"定位位置失败: {e}")
            
            # 打印更多调试信息
            print("尝试获取下拉列表中的所有选项...")
            try:
                all_options = await page.query_selector_all(
                    '//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    '//div[contains(@class, "d-options-wrapper")]'
                    '//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    '/div'
                )
                print(f"找到 {len(all_options)} 个选项")
                
                # 打印前3个选项的文本内容
                for i, option in enumerate(all_options[:3]):
                    option_text = await option.inner_text()
                    print(f"选项 {i+1}: {option_text.strip()[:50]}...")
                    
            except Exception as e:
                print(f"获取选项列表失败: {e}")
                
            # 截图保存（取消注释使用）
            # await page.screenshot(path=f"location_error_{location}.png")
            return False

    async def main(self):
        await self.upload()


