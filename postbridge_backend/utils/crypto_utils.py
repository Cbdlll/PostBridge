# 服务端加密工具
# 与客户端 crypto.py 配套使用

import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 共享密钥（必须与客户端一致）
SECRET_KEY = b'SAU_LOGIN_CLIENT_2026_SECURE_KEY'  # 32字节


def decrypt_cookie(encrypted_data: str) -> dict:
    """
    解密Cookie数据
    
    Args:
        encrypted_data: Base64编码的加密数据
    
    Returns:
        Cookie字典（Playwright storage_state格式）
    
    Raises:
        ValueError: 解密失败
    """
    try:
        # Base64解码
        raw = base64.b64decode(encrypted_data)
        
        # 分离nonce和密文
        nonce = raw[:12]
        ciphertext = raw[12:]
        
        # 创建AESGCM实例
        aesgcm = AESGCM(SECRET_KEY)
        
        # 解密
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        # 反序列化
        return json.loads(plaintext.decode('utf-8'))
    
    except Exception as e:
        raise ValueError(f"Cookie解密失败: {e}")


def encrypt_cookie(cookie_data: dict) -> str:
    """
    加密Cookie数据（用于测试）
    
    Args:
        cookie_data: Cookie字典
    
    Returns:
        Base64编码的加密数据
    """
    import os
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(SECRET_KEY)
    plaintext = json.dumps(cookie_data, ensure_ascii=False).encode('utf-8')
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    
    return base64.b64encode(nonce + ciphertext).decode('utf-8')
