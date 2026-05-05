# -*- coding: utf-8 -*-
"""
继续任务 API - 视频生成功能
从 app.py 解耦出来的独立模块
"""
import os
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify

from conf import BASE_DIR, DATABASE_PATH, RUNTIME_DIR
from ai_service.video_client import get_video_client, VideoGenerationError

# 创建 Blueprint
continue_task_bp = Blueprint('continue_task', __name__)


# Provider 配置映射（API key 字段、环境变量、模型字段、默认模型）
PROVIDER_CONFIG = {
    'doubao': {
        'api_key_field': 'doubaoApiKey',
        'env_var': 'DOUBAO_API_KEY',
        'model_field': 'doubaoModel',
        'default_model': 'doubao-seedance-1-5-pro-251215',
    },
    'sora': {  # 中转站（原中转站2）
        'api_key_field': 'transit2ApiKey',  # 使用 transit2ApiKey
        'env_var': 'TRANSIT2_API_KEY',
        'model_field': 'transit2Model',  # 使用 transit2Model
        'default_model': 'sora-2',
    },
    'wanxiang': {
        'api_key_field': 'wanApiKey',
        'env_var': 'DASHSCOPE_API_KEY',
        'model_field': 'wanxiangModel',
        'default_model': 'wan2.6-t2v',
    },
}


def get_video_params(video_config: dict) -> dict:
    """
    从 video_config 中提取视频生成参数
    根据 provider 自动获取对应的 API key 和 model
    """
    provider = video_config.get('provider', 'mock')
    
    # 获取 provider 配置
    cfg = PROVIDER_CONFIG.get(provider, {})
    api_key_field = cfg.get('api_key_field', 'apiKey')
    env_var = cfg.get('env_var', 'VIDEO_API_KEY')
    model_field = cfg.get('model_field')
    default_model = cfg.get('default_model')
    
    # 获取 API Key: config > 环境变量
    api_key = video_config.get(api_key_field, '') or os.getenv(env_var, '')
    # 获取模型
    model = video_config.get(model_field, default_model) if model_field else None
    
    return {
        'provider': provider,
        'api_key': api_key,
        'model': model,
        'resolution': video_config.get('resolution', '720p'),
        'duration': video_config.get('duration', 5),
        'shot_type': video_config.get('shotType', 'single'),
        'watermark': video_config.get('watermark', False),
        'mock_video_url': video_config.get('mockVideoUrl', ''),
    }


@continue_task_bp.route('/api/tasks/<int:task_id>/continue', methods=['PUT'])
def continue_task_with_video(task_id):
    """
    继续AI任务:更新选中的文案并开始视频生成
    输入: title, description, tags, video_prompt, video_config
    流程: 更新任务字段 -> 触发视频生成
    """
    # 延迟导入避免循环依赖
    from app import trigger_auto_publish
    
    data = request.get_json()
    
    title = data.get('title', '')
    description = data.get('description', '')
    tags = data.get('tags', [])
    video_prompt = data.get('video_prompt', '')
    video_config = data.get('video_config', {})
    
    if not video_prompt:
        return jsonify({"code": 400, "msg": "缺少视频提示词"}), 400
    
    try:
        # 获取任务详情
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM creation_tasks WHERE id = ?', (task_id,))
            task_row = cursor.fetchone()
            
            if not task_row:
                return jsonify({"code": 404, "msg": "任务不存在"}), 404
            
            task = dict(task_row)
        
        # 更新任务字段
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE creation_tasks 
                SET title = ?, description = ?, tags = ?, prompt = ?, 
                    status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                title,
                description,
                json.dumps(tags, ensure_ascii=False),
                video_prompt,
                'video_pending',
                task_id
            ))
            conn.commit()
        
        print(f"✅ 任务已更新: ID={task_id}, 开始视频生成")
        
        # 获取视频参数
        params = get_video_params(video_config)
        
        # 调试日志
        key_preview = f"{params['api_key'][:10]}...{params['api_key'][-4:]}" if params['api_key'] and len(params['api_key']) > 14 else "(empty)"
        print(f"📋 [视频生成] provider={params['provider']}, model={params['model']}, duration={params['duration']}s, api_key={key_preview}")
        
        def generate_and_publish():
            try:
                # 更新状态为 generating
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE creation_tasks SET status = ? WHERE id = ?', 
                        ('video_generating', task_id)
                    )
                    conn.commit()
                
                output_dir = str(Path(RUNTIME_DIR / "data/videos"))
                
                # 构建客户端参数
                client_kwargs = {
                    'provider': params['provider'],
                    'output_dir': output_dir,
                    'resolution': params['resolution'],
                    'duration': params['duration'],
                }
                
                # 添加 API key（非空时）
                if params['api_key']:
                    client_kwargs['api_key'] = params['api_key']
                
                # 添加可选参数
                if params['model']:
                    client_kwargs['model'] = params['model']
                if params['shot_type']:
                    client_kwargs['shot_type'] = params['shot_type']
                if params['watermark'] is not None:
                    client_kwargs['watermark'] = params['watermark']
                if params['provider'] == 'mock' and params['mock_video_url']:
                    client_kwargs['mock_video_url'] = params['mock_video_url']
                
                client = get_video_client(**client_kwargs)
                
                # 生成视频
                result = client.generate_video(video_prompt)
                video_task_id = result.get('task_id')
                
                # 保存视频任务ID
                with sqlite3.connect(DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'UPDATE creation_tasks SET video_task_id = ? WHERE id = ?', 
                        (video_task_id, task_id)
                    )
                    conn.commit()
                
                is_mock_mode = result.get('_mock') or params['provider'] == 'mock'
                if is_mock_mode:
                    print(f"🎭 [Mock] 模式已启用，将使用预设视频URL")
                
                # 轮询等待视频完成
                if hasattr(client, 'wait_for_completion'):
                    try:
                        final_result = client.wait_for_completion(video_task_id)
                        video_url = final_result.get('video_url')
                        
                        # 下载视频到本地
                        local_path = None
                        if video_url:
                            try:
                                platform_str = task.get('platform_str', 'douyin')
                                platform_name_map = {
                                    'douyin': '抖音', 'xhs': '小红书', 'ks': '快手',
                                    'wx': '视频号', 'bilibili': 'B站'
                                }
                                platform_display_name = platform_name_map.get(platform_str, '抖音')
                                
                                topic_name = task.get('topic', f'task_{task_id}')
                                display_filename = f"{topic_name}_{platform_display_name}-AI"
                                temp_filename = f"{display_filename}.mp4"
                                
                                local_path = client.download_video(video_url, temp_filename)
                                
                                # 添加到素材库
                                if local_path:
                                    video_uuid = str(uuid.uuid1())
                                    uuid_filename = f"{video_uuid}_{display_filename}.mp4"
                                    
                                    video_path = Path(local_path)
                                    new_video_path = video_path.parent / uuid_filename
                                    if video_path.exists():
                                        video_path.rename(new_video_path)
                                        local_path = str(new_video_path)
                                    
                                    file_size_mb = round(new_video_path.stat().st_size / (1024 * 1024), 2) if new_video_path.exists() else 0
                                    
                                    with sqlite3.connect(DATABASE_PATH) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('''
                                            INSERT INTO file_records (filename, filesize, file_path)
                                            VALUES (?, ?, ?)
                                        ''', (display_filename, file_size_mb, uuid_filename))
                                        conn.commit()
                                    
                                    print(f"📦 视频已添加到素材库: {uuid_filename} ({file_size_mb}MB)")
                                    
                            except Exception as e:
                                print(f"⚠️ 视频下载失败: {e}")
                        
                        # 更新任务状态
                        with sqlite3.connect(DATABASE_PATH) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE creation_tasks 
                                SET status = ?, video_url = ?, local_video_path = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', ('video_completed', video_url, local_path, task_id))
                            conn.commit()
                        
                        print(f"✅ 视频生成完成: task_id={task_id}, url={video_url}")
                        
                        # 触发自动发布
                        if task.get('auto_publish') and task.get('account_id') and local_path:
                            print(f"🚀 满足自动发布条件，准备发布...")
                            trigger_auto_publish(task_id)
                        else:
                            print(f"⚠️ 不满足自动发布条件，跳过自动发布")
                            
                    except VideoGenerationError as e:
                        _update_task_error(task_id, str(e))
                        print(f"❌ 视频生成失败: {e}")
                
            except Exception as e:
                _update_task_error(task_id, str(e))
                print(f"❌ 视频生成执行失败: {e}")
        
        # 后台线程执行
        threading.Thread(target=generate_and_publish, daemon=True).start()
        
        return jsonify({
            "code": 200,
            "msg": "任务已更新,视频生成中",
            "data": {"task_id": task_id, "status": "video_pending"}
        }), 200
        
    except Exception as e:
        print(f"继续任务失败: {e}")
        return jsonify({"code": 500, "msg": f"继续任务失败: {str(e)}", "data": None}), 500


def _update_task_error(task_id: int, error_msg: str):
    """更新任务错误状态"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE creation_tasks ADD COLUMN error_message TEXT")
        except sqlite3.OperationalError:
            pass
        cursor.execute(
            'UPDATE creation_tasks SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
            ('video_failed', error_msg, task_id)
        )
        conn.commit()
