import string
import random
import requests

def generate_random_prefix(length=9):
    """生成随机的字母和数字组合作为邮箱前缀"""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def run_test():
    # 用户输入需要注册测试的数量
    try:
        count = int(input("请输入需要生成的账号数量: "))
    except ValueError:
        print("请输入有效的数字")
        return

    # 目标接口和请求头
    url = "https://northmaples.top/api/v1/passport/auth/register"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Language": "zh-CN"
    }

    print(f"\n开始执行测试，共 {count} 个请求...\n")

    # 循环发送请求
    for i in range(count):
        # 1. 动态生成随机邮箱和固定密码
        email_prefix = generate_random_prefix()
        email = f"{email_prefix}@gmail.com"
        password = "12345678"
        
        # 2. 构造表单数据 (Form Data)
        data = {
            "email": email,
            "password": password,
            "invite_code": "",
            "email_code": ""
        }

        try:
            # 3. 发送 POST 请求
            response = requests.post(url, data=data, headers=headers, timeout=10)
            
            # 4. 解析响应 JSON
            if response.status_code == 200:
                res_json = response.json()
                
                # 检查接口返回的状态
                if res_json.get("status") == "success" or res_json.get("data"):
                    token = res_json["data"]["token"]
                    # 5. 按要求格式化输出目标链接
                    print(f"https://ss88.beifengyuns.top/s/{token}")
                else:
                    print(f"第 {i+1} 个账号注册接口返回错误: {res_json.get('message')}")
            else:
                print(f"第 {i+1} 个请求失败，HTTP 状态码: {response.status_code}")
                
        except Exception as e:
            print(f"第 {i+1} 个请求发送异常: {e}")

if __name__ == "__main__":
    run_test()
