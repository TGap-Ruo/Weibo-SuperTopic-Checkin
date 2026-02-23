from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from wb import WeiboChaohuaSignin, batch_sign

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 配置文件路径
CONFIG_FILE = 'config.json'

# 初始化配置文件
def init_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'cookies': []}, f, ensure_ascii=False, indent=4)

# 读取Cookie列表
def get_cookies():
    init_config()
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('cookies', [])

# 保存Cookie列表
def save_cookies(cookies):
    init_config()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({'cookies': cookies}, f, ensure_ascii=False, indent=4)

# 主页
@app.route('/')
def index():
    cookies = get_cookies()
    # 简化显示Cookie（只展示前20位+后10位）
    cookie_display = []
    for idx, cookie in enumerate(cookies):
        if len(cookie) > 30:
            show_cookie = f"{cookie[:20]}...{cookie[-10:]}"
        else:
            show_cookie = cookie
        cookie_display.append({
            'index': idx + 1,
            'show': show_cookie,
            'raw': cookie
        })
    return render_template('index.html', cookies=cookie_display)

# 添加Cookie
@app.route('/add_cookie', methods=['POST'])
def add_cookie():
    cookie = request.form.get('cookie', '').strip()
    if not cookie:
        return jsonify({'status': 'error', 'msg': 'Cookie不能为空！'})
    
    cookies = get_cookies()
    if cookie in cookies:
        return jsonify({'status': 'error', 'msg': '该Cookie已存在！'})
    
    cookies.append(cookie)
    save_cookies(cookies)
    return jsonify({'status': 'success', 'msg': 'Cookie添加成功！'})

# 删除Cookie
@app.route('/delete_cookie', methods=['POST'])
def delete_cookie():
    index = int(request.form.get('index', -1)) - 1
    cookies = get_cookies()
    
    if index < 0 or index >= len(cookies):
        return jsonify({'status': 'error', 'msg': '无效的Cookie索引！'})
    
    cookies.pop(index)
    save_cookies(cookies)
    return jsonify({'status': 'success', 'msg': 'Cookie删除成功！'})

# 执行签到
@app.route('/run_sign', methods=['POST'])
def run_sign():
    cookies = get_cookies()
    if not cookies:
        return jsonify({'status': 'error', 'msg': '暂无可用的Cookie，请先添加！'})
    
    try:
        # 执行批量签到
        results = batch_sign(cookies)
        # 整理日志
        all_logs = []
        for res in results:
            all_logs.extend(res['result']['logs'])
        
        return jsonify({
            'status': 'success',
            'msg': '签到任务执行完成！',
            'logs': [log['message'] for log in all_logs],
            'results': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'msg': f'执行失败：{str(e)}'})

if __name__ == '__main__':
    # 生产环境请关闭debug，修改host为0.0.0.0
    app.run(host='0.0.0.0', port=5000, debug=False)