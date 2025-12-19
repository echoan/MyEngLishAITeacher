'''
Author: Chengya
Description: Description
Date: 2025-12-09 23:01:38
LastEditors: Chengya
LastEditTime: 2025-12-19 10:12:06
'''
import os
import google.generativeai as genai

# 1. 设置代理
# 如果您查到的端口是 7897，请把下面的 7890 改成 7897
os.environ["HTTP_PROXY"] = "http://127.0.0.1:17890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:17890"

# 2. 填入您的新 API Key (千万不要用之前泄露的那个！)
GOOGLE_API_KEY = "AIzaSyD_dhUU60Cf9T4fgUZm412L1HuPBt7toCo"

# 3. 关键配置：transport='rest'
# Mac 上如果出现 SSL/TLS 握手错误，加这个参数通常能解决
genai.configure(api_key=GOOGLE_API_KEY, transport='rest')

print("正在连接 Google (Mac)...")

try:
    # 打印所有可用模型
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"可用模型: {m.name}")

    # 单独测试一下 Flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("你好，请回复“连接成功”")
    print("\n-----------------")
    print(f"测试结果: {response.text}")

except Exception as e:
    print(f"\n发生错误了: {e}")