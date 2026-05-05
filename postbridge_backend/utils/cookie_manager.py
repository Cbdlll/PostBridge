# -*- coding: utf-8 -*-
"""
Cookie智能管理器 - 支持有效期检测和交互式刷新
用于管理抖音账号的登录状态
"""
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright

from conf import BASE_DIR, LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import douyin_logger


class DouyinCookieManager:
    """抖音Cookie管理器"""
    
    COOKIE_CHECK_URL = "https://creator.douyin.com/creator-micro/content/upload"
    LOGIN_URL = "https://creator.douyin.com/"
    
    def __init__(self, account_file: str):
        self.account_file = Path(account_file)
        self.last_check_time: Optional[datetime] = None
        self.is_valid: bool = False
    
    async def check_validity(self) -> bool:
        """检查Cookie是否有效"""
        if not self.account_file.exists():
            douyin_logger.warning(f"Cookie文件不存在: {self.account_file}")
            return False
        
        try:
            async with async_playwright() as playwright:
                chrome_args = [
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-translate',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-infobars',
                    '--disable-notifications',
                    '--lang=zh-CN',
                ]
                launch_options = {
                    'headless': True,
                    'args': chrome_args
                }
                if LOCAL_CHROME_PATH:
                    launch_options['executable_path'] = LOCAL_CHROME_PATH
                browser = await playwright.chromium.launch(**launch_options)
                context = await browser.new_context(
                    storage_state=str(self.account_file),
                    viewport={'width': 1280, 'height': 800},
                    locale='zh-CN'
                )
                context = await set_init_script(context)
                
                # 注入唤端拦截脚本
                await context.add_init_script("""
                    (function() {
                        const originalCreateElement = document.createElement;
                        document.createElement = function(tagName) {
                            const element = originalCreateElement.call(document, tagName);
                            if (tagName.toLowerCase() === 'iframe') {
                                try {
                                    Object.defineProperty(element, 'src', {
                                        set: function(value) {
                                            if (value && !value.startsWith('http') && !value.startsWith('//') && 
                                                !value.startsWith('about:') && !value.startsWith('javascript:')) {
                                                return;
                                            }
                                            element.setAttribute('src', value);
                                        },
                                        get: function() { return element.getAttribute('src'); },
                                        configurable: true
                                    });
                                } catch (e) {}
                                
                                const originalSetAttribute = element.setAttribute;
                                element.setAttribute = function(name, value) {
                                    if (name.toLowerCase() === 'src' && value && 
                                        !value.startsWith('http') && !value.startsWith('//') && 
                                        !value.startsWith('about:') && !value.startsWith('javascript:')) {
                                        return;
                                    }
                                    return originalSetAttribute.call(this, name, value);
                                };
                            }
                            return element;
                        };
                    })();
                """)

                page = await context.new_page()

                # 网络层拦截
                async def intercept_external_protocols(route, request):
                    if not request.url.startswith(("http:", "https:", "file:", "data:", "chrome-extension:", "blob:")):
                        try: await route.abort()
                        except: pass
                    else:
                        try: await route.continue_()
                        except: pass

                await page.route("**/*", intercept_external_protocols)
                
                await page.goto(self.COOKIE_CHECK_URL)
                
                try:
                    await page.wait_for_url(self.COOKIE_CHECK_URL, timeout=5000)
                except:
                    await context.close()
                    await browser.close()
                    return False
                
                # 检查是否需要登录
                if await page.get_by_text('手机号登录').count() or \
                   await page.get_by_text('扫码登录').count():
                    await context.close()
                    await browser.close()
                    return False
                
                await context.close()
                await browser.close()
                
                self.is_valid = True
                self.last_check_time = datetime.now()
                return True
                
        except Exception as e:
            douyin_logger.error(f"检查Cookie有效性时出错: {e}")
            return False
    
    async def refresh_interactive(self, timeout_seconds: int = 600) -> bool:
        """
        交互式刷新Cookie - 弹出浏览器让用户完成登录和所有验证
        
        Args:
            timeout_seconds: 最长等待时间（秒），默认10分钟
        
        Returns:
            是否刷新成功
        """
        douyin_logger.info("正在启动交互式登录，请在浏览器中完成登录和验证...")
        
        try:
            async with async_playwright() as playwright:
                chrome_args = [
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-translate',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-infobars',
                    '--disable-notifications',
                    '--lang=zh-CN',
                    # 移除 --disable-popup-blocking
                ]
                launch_options = {
                    'headless': False,
                    'args': chrome_args
                }
                if LOCAL_CHROME_PATH:
                    launch_options['executable_path'] = LOCAL_CHROME_PATH
                browser = await playwright.chromium.launch(**launch_options)
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    locale='zh-CN'
                )
                
                # 注入唤端拦截脚本
                await context.add_init_script("""
                    (function() {
                        const originalCreateElement = document.createElement;
                        document.createElement = function(tagName) {
                            const element = originalCreateElement.call(document, tagName);
                            if (tagName.toLowerCase() === 'iframe') {
                                try {
                                    Object.defineProperty(element, 'src', {
                                        set: function(value) {
                                            if (value && !value.startsWith('http') && !value.startsWith('//') && 
                                                !value.startsWith('about:') && !value.startsWith('javascript:')) {
                                                console.log('[AntiGravity] Blocked iframe src (property):', value);
                                                return;
                                            }
                                            element.setAttribute('src', value);
                                        },
                                        get: function() { return element.getAttribute('src'); },
                                        configurable: true
                                    });
                                } catch (e) {}
                                
                                const originalSetAttribute = element.setAttribute;
                                element.setAttribute = function(name, value) {
                                    if (name.toLowerCase() === 'src' && value && 
                                        !value.startsWith('http') && !value.startsWith('//') && 
                                        !value.startsWith('about:') && !value.startsWith('javascript:')) {
                                        console.log('[AntiGravity] Blocked iframe src (setAttribute):', value);
                                        return;
                                    }
                                    return originalSetAttribute.call(this, name, value);
                                };
                            }
                            return element;
                        };
                    })();
                """)
                
                context = await set_init_script(context)
                page = await context.new_page()

                # 网络层拦截
                async def intercept_external_protocols(route, request):
                    if not request.url.startswith(("http:", "https:", "file:", "data:", "chrome-extension:", "blob:")):
                        try: await route.abort()
                        except: pass
                    else:
                        try: await route.continue_()
                        except: pass

                await page.route("**/*", intercept_external_protocols)
                
                # 导航到登录页
                await page.goto(self.LOGIN_URL)
                
                # 等待用户完成登录（包括所有验证步骤）
                check_interval = 3
                max_checks = timeout_seconds // check_interval
                
                for i in range(max_checks):
                    await asyncio.sleep(check_interval)
                    
                    # 检查是否已登录
                    try:
                        if "creator-micro" in page.url and "login" not in page.url.lower():
                            # 尝试访问上传页面确认
                            await page.goto(self.COOKIE_CHECK_URL)
                            await page.wait_for_url("**/content/upload", timeout=5000)
                            
                            if not await page.get_by_text('手机号登录').count() and \
                               not await page.get_by_text('扫码登录').count():
                                break
                    except:
                        continue
                    
                    if i % 10 == 0:
                        douyin_logger.info(f"等待用户完成登录... ({i * check_interval}/{timeout_seconds}秒)")
                else:
                    douyin_logger.error("登录超时")
                    await browser.close()
                    return False
                
                # 保存新Cookie
                await context.storage_state(path=str(self.account_file))
                douyin_logger.success("Cookie刷新成功!")
                
                await context.close()
                await browser.close()
                
                self.is_valid = True
                self.last_check_time = datetime.now()
                return True
                
        except Exception as e:
            douyin_logger.error(f"交互式登录失败: {e}")
            return False
    
    async def ensure_valid(self) -> bool:
        """
        确保Cookie有效 - 如果无效则触发交互式刷新
        
        Returns:
            Cookie是否有效
        """
        if await self.check_validity():
            return True
        
        douyin_logger.warning("Cookie已失效，需要重新登录")
        return await self.refresh_interactive()
