#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博超话批量签到核心模块
作者: emper0r
版本: v1.3 (适配Web版)
"""

import os
import re
import sys
import json
import time
import random
import requests
from urllib.parse import urlencode, quote

class WeiboChaohuaSignin:
    def __init__(self, cookie, account_index=1, total_accounts=1):
        self.account_index = account_index
        self.total_accounts = total_accounts
        self.account_name = f"账户{account_index}"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
        # 处理Cookie编码问题
        self.cookie = self.clean_cookie(cookie)
        self.session.headers['Cookie'] = self.cookie
        
        self.xsrf_token = self.get_xsrf_token()
        
        if self.xsrf_token:
            self.session.headers['X-XSRF-TOKEN'] = self.xsrf_token
        
        # 配置
        self.sign_interval = 1.5  # 签到间隔(秒)
        self.account_interval = 10  # 账户间间隔(秒)
        # 新增：日志存储（用于Web端展示）
        self.logs = []

    def clean_cookie(self, cookie):
        """清理Cookie，处理编码问题"""
        try:
            cookie = cookie.strip().replace('\n', '').replace('\r', '')
            if isinstance(cookie, bytes):
                cookie = cookie.decode('utf-8', errors='ignore')
            cookie = ''.join(char for char in cookie if ord(char) < 128)
            return cookie
        except Exception as e:
            self.log(f"Cookie处理失败: {str(e)}", 'ERROR')
            return cookie

    def get_xsrf_token(self):
        """从Cookie中提取XSRF-TOKEN"""
        try:
            match = re.search(r'XSRF-TOKEN=([^;]+)', self.cookie)
            if match:
                return match.group(1)
        except:
            pass
        return None

    def get_user_info(self):
        """获取用户基本信息"""
        try:
            sub_match = re.search(r'SUB=([^;]+)', self.cookie)
            if sub_match:
                return f"用户{sub_match.group(1)[:8]}..."
        except:
            pass
        return "未知用户"

    def log(self, message, level='INFO'):
        """日志输出（新增：同时存储到logs列表）"""
        timestamp = time.strftime('%H:%M:%S', time.localtime())
        symbols = {
            'INFO': 'ℹ️',
            'SUCCESS': '✅', 
            'ERROR': '❌',
            'WARNING': '⚠️'
        }
        account_prefix = f"[{self.account_name}] " if self.total_accounts > 1 else ""
        log_msg = f"[{timestamp}] {symbols.get(level, 'ℹ️')} {account_prefix}{message}"
        # 存储日志供Web端展示
        self.logs.append({
            'time': timestamp,
            'level': level,
            'message': log_msg
        })
        print(log_msg)
        return log_msg

    def fetch_chaohua_list(self, page=1, collected=None):
        """获取超话列表"""
        if collected is None:
            collected = []
            
        self.log(f"正在获取第 {page} 页超话列表...")
        
        url = f"https://weibo.com/ajax/profile/topicContent"
        params = {
            'tabid': '231093_-_chaohua',
            'page': page
        }
        
        try:
            headers = {
                'Referer': 'https://weibo.com/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                raise Exception(f"HTTP Error: {response.status_code}")
            if not response.text:
                raise Exception("响应内容为空")
            
            data = response.json()
            if data.get('ok') != 1:
                error_msg = data.get('msg', '未知错误')
                if 'login' in error_msg.lower() or 'cookie' in error_msg.lower():
                    raise Exception(f"登录状态失效，请更新Cookie: {error_msg}")
                raise Exception(f"API返回错误: {error_msg}")
            
            api_data = data.get('data', {})
            chaohua_list = api_data.get('list', [])
            
            if not chaohua_list:
                return collected
            
            for item in chaohua_list:
                oid = item.get('oid', '')
                if oid.startswith('1022:'):
                    chaohua_id = oid[5:]
                    chaohua_name = item.get('topic_name', '')
                    if chaohua_id and chaohua_name:
                        collected.append({
                            'id': chaohua_id,
                            'name': chaohua_name
                        })
            
            max_page = api_data.get('max_page', 1)
            if page < max_page:
                time.sleep(0.8)
                return self.fetch_chaohua_list(page + 1, collected)
            
            return collected
            
        except requests.exceptions.RequestException as e:
            self.log(f"网络请求失败: {str(e)}", 'ERROR')
            raise
        except json.JSONDecodeError as e:
            self.log(f"JSON解析失败，响应内容: {response.text[:200]}...", 'ERROR')
            raise
        except Exception as e:
            self.log(f"获取超话列表失败: {str(e)}", 'ERROR')
            raise

    def sign_chaohua(self, chaohua_id, chaohua_name):
        """签到单个超话"""
        url = "https://weibo.com/p/aj/general/button"
        
        params = {
            'api': 'http://i.huati.weibo.com/aj/super/checkin',
            'id': chaohua_id,
            'location': 'page_100808_super_index',
            '__rnd': int(time.time() * 1000)
        }
        
        try:
            headers = {
                'Referer': f'https://weibo.com/p/{chaohua_id}/super_index',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {'success': False, 'msg': f'HTTP错误: {response.status_code}'}
            
            data = response.json()
            code = str(data.get('code', ''))
            msg = data.get('msg', '未知错误')
            
            success_codes = ['100000', '382004', '382010']
            is_success = code in success_codes
            
            return {
                'success': is_success,
                'code': code,
                'msg': msg,
                'already_signed': code == '382004'
            }
            
        except requests.exceptions.RequestException as e:
            return {'success': False, 'msg': f'网络请求失败: {str(e)}'}
        except json.JSONDecodeError:
            return {'success': False, 'msg': '响应格式错误'}
        except Exception as e:
            return {'success': False, 'msg': f'签到失败: {str(e)}'}

    def run(self):
        """单个账户执行签到（返回结果统计）"""
        user_info = self.get_user_info()
        self.log(f"🚀 开始执行签到任务 ({user_info})")
        
        if not self.xsrf_token:
            self.log("⚠️ 未找到XSRF-TOKEN，可能影响签到功能", 'WARNING')
        
        try:
            self.log("📋 正在获取超话列表...")
            chaohua_list = self.fetch_chaohua_list()
            
            if not chaohua_list:
                self.log("未获取到超话列表，请检查Cookie是否有效", 'WARNING')
                return {
                    'success': False,
                    'total': 0,
                    'success_count': 0,
                    'already_signed_count': 0,
                    'fail_count': 0,
                    'logs': self.logs
                }
            
            self.log(f"📊 成功获取到 {len(chaohua_list)} 个超话")
            
            success_count = 0
            already_signed_count = 0
            fail_count = 0
            
            for i, chaohua in enumerate(chaohua_list, 1):
                chaohua_id = chaohua['id']
                chaohua_name = chaohua['name']
                
                self.log(f"📝 正在签到 ({i}/{len(chaohua_list)}): {chaohua_name}")
                
                result = self.sign_chaohua(chaohua_id, chaohua_name)
                
                if result['success']:
                    if result.get('already_signed'):
                        self.log(f"⚠️  [{chaohua_name}] {result['msg']}", 'WARNING')
                        already_signed_count += 1
                    else:
                        self.log(f"✅ [{chaohua_name}] {result['msg']}", 'SUCCESS')
                        success_count += 1
                else:
                    self.log(f"❌ [{chaohua_name}] {result['msg']}", 'ERROR')
                    fail_count += 1
                
                time.sleep(self.sign_interval)  # 签到间隔
            
            # 最终统计
            total = len(chaohua_list)
            self.log(f"📈 签到完成！总计 {total} 个超话，成功 {success_count} 个，已签到 {already_signed_count} 个，失败 {fail_count} 个")
            
            return {
                'success': True,
                'total': total,
                'success_count': success_count,
                'already_signed_count': already_signed_count,
                'fail_count': fail_count,
                'logs': self.logs
            }
            
        except Exception as e:
            self.log(f"签到任务执行失败: {str(e)}", 'ERROR')
            return {
                'success': False,
                'total': 0,
                'success_count': 0,
                'already_signed_count': 0,
                'fail_count': 0,
                'logs': self.logs
            }

# 新增：多账户批量执行
def batch_sign(cookies):
    """
    批量执行多个Cookie的签到
    :param cookies: Cookie列表
    :return: 汇总结果
    """
    total_accounts = len(cookies)
    results = []
    
    for idx, cookie in enumerate(cookies, 1):
        signer = WeiboChaohuaSignin(cookie, idx, total_accounts)
        result = signer.run()
        results.append({
            'account_index': idx,
            'user_info': signer.get_user_info(),
            'result': result
        })
        if idx < total_accounts:
            time.sleep(signer.account_interval)  # 账户间间隔
    
    return results