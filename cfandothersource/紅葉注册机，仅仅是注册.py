import requests
import json
import random
import string
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置全局基础 URL
BASE_URL = "https://jkl.redleaf.one"

# 初始化全局变量与线程锁
success_count = 0
counter_lock = threading.Lock()
print_lock = threading.Lock()

def generate_random_email():
    """随机生成 8 位前缀，并从指定的四个后缀中随机选择一个"""
    characters = string.ascii_letters + string.digits
    random_prefix = ''.join(random.choice(characters) for _ in range(8))
    email_suffixes = ["gmail.com", "qq.com", "163.com", "outlook.com"]
    return f"{random_prefix}@{random.choice(email_suffixes)}"

def single_register_task(task_id, total_count, password):
    """单个注册任务线程"""
    global success_count
    
    register_url = f"{BASE_URL}/next/passport/redeem/register"
    random_email = generate_random_email()
    
    register_headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Client-Type": "next",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }
    
    register_data = {
        "email": random_email,
        "email_code": "",
        "password": password,
        "code": "",
        "invite_code": "",
        "fingerprint": "e8414cf9a56d284109bc27cb3ba5bcb8"
    }
    
    try:
        response_reg = requests.post(register_url, headers=register_headers, json=register_data, timeout=15)
        
        try:
            reg_json = response_reg.json()
            is_success = response_reg.status_code == 200 and reg_json.get("success") is True
            
            with counter_lock:
                if is_success:
                    success_count += 1
            
            # 使用打印锁，防止多线程同时打印导致日志错乱
            with print_lock:
                if is_success:
                    auth_data_preview = reg_json.get("data", {}).get("auth_data", "")[:20]
                    print(f"[{task_id}/{total_count}] 🚀 尝试注册: {random_email} -> ✅ 成功！当前累计成功: {success_count} 个")
                else:
                    print(f"[{task_id}/{total_count}] 🚀 尝试注册: {random_email} -> ❌ 失败！状态码: {response_reg.status_code}, 原因: {reg_json}")
                    
        except json.JSONDecodeError:
            with print_lock:
                raw_text = response_reg.text.strip()
                print(f"[{task_id}/{total_count}] 🚀 尝试注册: {random_email} -> ❌ 失败！未返回JSON(状态码:{response_reg.status_code})。前50字: {raw_text[:50]}")
                
    except Exception as e:
        with print_lock:
            print(f"[{task_id}/{total_count}] 🚀 尝试注册: {random_email} -> ❌ 网络异常: {e}")

def main():
    global success_count
    success_count = 0  # 每次运行重置计数器
    password = "12345678"
    
    try:
        # 1. 动态输入注册总数
        user_input_total = input("👉 请输入你想注册的【总账号个数】(例如 100): ")
        total_count = int(user_input_total)
        
        # 2. 动态输入并发线程数
        user_input_threads = input("🔥 请输入【并发线程数】(建议 5 到 20 之间，过高可能被防火墙拦截): ")
        max_workers = int(user_input_threads)
        
        if total_count <= 0 or max_workers <= 0:
            print("❌ 请输入大于 0 的数字！")
            return
            
        print(f"\n⚡ 正在启动高并发线程池... 总目标: {total_count} | 最大并发数: {max_workers}")
        print("=" * 60)
        
        start_time = time.time()
        
        # 3. 创建线程池并派发任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(single_register_task, i, total_count, password) 
                for i in range(1, total_count + 1)
            ]
            # 等待所有线程全部执行完毕
            for future in as_completed(futures):
                pass
                
        end_time = time.time()
        time_used = round(end_time - start_time, 2)
        
        print("=" * 60)
        print(f"🎉 批量测试结束！耗时: {time_used} 秒")
        print(f"📊 统计结果 -> 目标发送: {total_count} 个 | 成功注册: {success_count} 个")
        
    except ValueError:
        print("❌ 输入错误！请输入纯数字。")

if __name__ == "__main__":
    main()
