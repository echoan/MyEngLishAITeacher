'''
Author: Chengya
Description: Description
Date: 2025-12-11 22:27:09
LastEditors: Chengya
LastEditTime: 2025-12-11 22:27:35
'''
# build_library.py - 这是一个独立的工具脚本，运行一次即可
import json
import requests
import time

# 1. 这里填入你想提前生成图片的单词列表
# 比如你可以放几百个进去
target_words = [
    "apple", "banana", "orange", "computer", "mountain",
    "ocean", "freedom", "ambitious", "galaxy", "telescope"
]

# 2. 简单的生成 URL 函数 (Pollinations)
def generate_static_url(word):
    # 为了保证图片风格统一且固定，我们可以把时间戳定死，或者用单词本身的哈希
    # 这样每次生成的 URL 都是一样的，浏览器也可以缓存
    seed = hash(word)
    prompt = f"Cartoon illustration of {word}, vector art, white background, vivid colors"
    encoded_prompt = requests.utils.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&seed={seed}"

# 3. 开始批量生成
library = {}
print(f"🚀 开始构建图库，共 {len(target_words)} 个单词...")

for word in target_words:
    url = generate_static_url(word)
    library[word] = url
    print(f"✅ Generated: {word}")
    # 稍微停顿一下，别把人家服务器刷崩了
    time.sleep(0.1)

# 4. 保存为 JSON 文件
filename = "static_images.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(library, f, indent=2, ensure_ascii=False)

print(f"\n🎉 图库构建完成！已保存到 {filename}")
print("请将此文件放在与 app.py 同一级目录下。")