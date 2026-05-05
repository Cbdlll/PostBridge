from pathlib import Path
from typing import List

from conf import BASE_DIR

SOCIAL_MEDIA_DOUYIN = "douyin"
SOCIAL_MEDIA_TENCENT = "tencent"
SOCIAL_MEDIA_TIKTOK = "tiktok"
SOCIAL_MEDIA_BILIBILI = "bilibili"
SOCIAL_MEDIA_KUAISHOU = "kuaishou"


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    """
    设置反检测脚本：
    1. 注入 stealth.min.js (来自 puppeteer-extra-plugin-stealth)
    2. 额外强制覆盖 navigator.webdriver (多层防护)
    """
    # 1. 注入 stealth.min.js
    stealth_js_path = Path(BASE_DIR / "utils/stealth.min.js")
    await context.add_init_script(path=stealth_js_path)
    
    # 2. 额外注入强制覆盖 navigator.webdriver 的脚本 (双重保险)
    # 某些深层检测可能绕过 stealth.js，此处再次强制覆盖
    await context.add_init_script("""
        // 强制移除 navigator.webdriver
        (function() {
            // 方法1: 删除 webdriver 属性
            try {
                delete Object.getPrototypeOf(navigator).webdriver;
            } catch(e) {}
            
            // 方法2: 重新定义为 undefined
            try {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
            } catch(e) {}
            
            // 方法3: 覆盖原型链上的 getter
            try {
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            } catch(e) {}
            
            // 方法4: 隐藏自动化相关属性
            try {
                // 移除 window.cdc_adoQpoasnfa76pfcZLmcfl_* 等 Chrome Driver 痕迹
                for (let prop in window) {
                    if (prop.match(/^cdc_|^__webdriver_|^_Selenium_|^calledSelenium|^_phantom|^__nightmare|^domAutomation|^domAutomationController/i)) {
                        try { delete window[prop]; } catch(e) {}
                    }
                }
            } catch(e) {}
            
            // 方法5: 伪装 chrome.runtime
            try {
                if (window.chrome && !window.chrome.runtime) {
                    window.chrome.runtime = {};
                }
            } catch(e) {}
            
            // 方法6: 修复 iframe 中的 contentWindow
            try {
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get: function() {
                        const iframe = this;
                        return new Proxy(iframe.__proto__.contentWindow.__lookupGetter__('contentWindow').call(iframe) || {}, {
                            get: (target, prop) => {
                                if (prop === 'navigator') {
                                    return new Proxy(target.navigator || navigator, {
                                        get: (nav, navProp) => {
                                            if (navProp === 'webdriver') return undefined;
                                            return nav[navProp];
                                        }
                                    });
                                }
                                return target[prop];
                            }
                        });
                    }
                });
            } catch(e) {}
        })();
    """)
    
    return context


# ========================
# 性能优化函数
# ========================

async def setup_resource_blocking(page, block_images: bool = True, block_fonts: bool = True, block_analytics: bool = True):
    """
    设置资源拦截，阻止加载不必要的资源以提升性能
    
    Args:
        page: Playwright 页面对象
        block_images: 是否阻止加载图片（视频封面除外）
        block_fonts: 是否阻止加载自定义字体
        block_analytics: 是否阻止加载分析/追踪脚本
    
    节省资源说明:
        - 图片: 通常占页面加载 50-70% 流量
        - 字体: 每个字体文件约 100KB-500KB
        - 分析脚本: 减少不必要的网络请求和 CPU 占用
    """
    # 分析脚本域名黑名单
    analytics_domains = [
        'google-analytics.com',
        'googletagmanager.com',
        'hotjar.com',
        'clarity.ms',
        'mixpanel.com',
        'segment.com',
        'amplitude.com',
        'sentry.io',
        'bugsnag.com',
        'logrocket.com',
        'fullstory.com',
        'heap.io',
        'intercom.io',
        'crisp.chat',
        'zendesk.com',
        'freshdesk.com',
    ]
    
    async def route_handler(route, request):
        """拦截请求并根据规则阻止或放行"""
        url = request.url.lower()
        resource_type = request.resource_type
        
        # 阻止图片（但允许视频相关）
        if block_images and resource_type == 'image':
            # 允许视频缩略图、封面等必要图片
            if not any(kw in url for kw in ['video', 'cover', 'thumb', 'poster', 'avatar', 'upload']):
                await route.abort()
                return
        
        # 阻止自定义字体
        if block_fonts and resource_type == 'font':
            await route.abort()
            return
        
        # 阻止分析脚本
        if block_analytics and resource_type == 'script':
            for domain in analytics_domains:
                if domain in url:
                    await route.abort()
                    return
        
        # 阻止大型媒体文件（非上传相关）
        if resource_type == 'media':
            # 允许上传相关的 media
            if 'upload' not in url and 'post' not in url:
                await route.abort()
                return
        
        # 放行其他请求
        await route.continue_()
    
    await page.route('**/*', route_handler)


def get_optimized_chrome_args() -> list:
    """
    获取优化的 Chrome 启动参数
    
    包含:
    - 反自动化检测参数
    - 内存优化参数
    - 性能优化参数
    """
    return [
        # 反自动化检测
        '--disable-blink-features=AutomationControlled',
        '--disable-automation',
        
        # 安全/沙箱
        '--no-sandbox',
        '--disable-setuid-sandbox',
        
        # 性能优化
        '--disable-dev-shm-usage',  # 避免 /dev/shm 内存不足
        '--disable-gpu',  # 禁用 GPU（headless 模式下更稳定）
        '--disable-software-rasterizer',
        
        # 减少资源占用
        '--disable-extensions',
        '--disable-plugins',
        '--disable-translate',
        '--disable-features=Translate',
        '--disable-sync',
        '--disable-background-networking',
        '--disable-default-apps',
        '--disable-hang-monitor',
        '--disable-prompt-on-repost',
        '--disable-domain-reliability',
        '--disable-client-side-phishing-detection',
        
        # UI简化
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-infobars',
        '--disable-notifications',
        '--disable-popup-blocking',
        '--disable-save-password-bubble',
        '--disable-component-update',
        
        # 语言和窗口
        '--lang=zh-CN',
        '--window-size=1280,800',
    ]


def get_optimized_context_options(storage_state: str = None) -> dict:
    """
    获取优化的浏览器上下文选项
    
    Args:
        storage_state: Cookie 存储路径
    
    Returns:
        dict: 上下文配置选项
    """
    options = {
        'viewport': {'width': 1280, 'height': 800},
        'locale': 'zh-CN',
        'timezone_id': 'Asia/Shanghai',
        'permissions': ['geolocation', 'notifications'],
        'geolocation': {'latitude': 39.9042, 'longitude': 116.4074},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        # 性能优化
        'ignore_https_errors': True,
        'java_script_enabled': True,
        'bypass_csp': False,
    }
    
    if storage_state:
        options['storage_state'] = storage_state
    
    return options
