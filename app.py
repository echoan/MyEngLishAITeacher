'''
Author: Chengya
Description: Description
Date: 2025-12-09 12:37:25
LastEditors: Chengya
LastEditTime: 2025-12-09 23:05:09
'''
import streamlit as st
import google.generativeai as genai
import json
import random
import requests
import time
from gtts import gTTS # 导入语音库
import io # 导入IO库用于处理音频流

# --- 1. 页面配置 ---
st.set_page_config(page_title="英语单词闪卡大师 (AI绘图+发音版)", page_icon="🎨")

# --- 2. 状态初始化 ---
if 'word_bank' not in st.session_state:
    st.session_state['word_bank'] = []
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = None
if 'quiz_state' not in st.session_state:
    st.session_state['quiz_state'] = 'IDLE'
if 'user_selection' not in st.session_state:
    st.session_state['user_selection'] = None
if 'generated_image_url' not in st.session_state:
    st.session_state['generated_image_url'] = None
    # ... 其他状态初始化 ...
if 'has_started' not in st.session_state:
    st.session_state['has_started'] = False # 默认为 False，表示还没开始过
    # 👇 新增：剩余单词池
if 'remaining_words' not in st.session_state:
    st.session_state['remaining_words'] = []
# 👇 新增：图片缓存字典 { "单词": "URL" }
if 'image_cache' not in st.session_state:
    st.session_state['image_cache'] = {}

# --- 3. 核心逻辑函数 ---

def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    return st.sidebar.text_input("请输入 Google Gemini API Key", type="password")

def generate_image_url(image_prompt):
    timestamp = int(time.time())
    encoded_prompt = requests.utils.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&t={timestamp}"
    return image_url

def generate_quiz(word, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-pro')
    # model = genai.GenerativeModel('gemini-1.5-flash')
    # model = genai.GenerativeModel('gemma-3-12b-it')
    prompt = f"""
    请针对单词 "{word}" 设计一道英语词汇测试题。

    核心任务：
    1. 为这个单词设计一个非常有创意、画面感极强、有助于记忆的场景。
    2. 将这个场景翻译成一段详细的【英文绘图提示词 (Image Generation Prompt)】。
    3. 英文提示词要求：包含主体、动作、环境、光线、艺术风格（如 cartoon style, digital art, vibrant colors）。

    请严格输出标准的 JSON 格式，不要包含 Markdown 标记。
    JSON 结构如下：
    {{
        "word": "{word}",
        "ipa": "单词音标",
        "image_gen_prompt": "Detailed English image generation prompt...",
        "visual_cue_cn": "简短的中文场景描述（备用）",
        "options": [
            {{"label": "A", "text": "错误中文释义1"}},
            {{"label": "B", "text": "正确中文释义"}},
            {{"label": "C", "text": "错误中文释义2"}},
            {{"label": "D", "text": "错误中文释义3"}}
        ],
        "correct_label": "B"
    }}
    注意：随机打乱正确选项位置。
    """

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI 生成解析失败: {e}")
        return None

def add_words():
    raw_text = st.session_state.new_words_input
    if raw_text.strip():
        new_list = [w.strip() for w in raw_text.split('\n') if w.strip()]

        # 1. 存入总词库 (去重逻辑可以以后再加，现在先直接存)
        st.session_state['word_bank'].extend(new_list)
        # 2. 👇 同时存入剩余单词池 (让新词也能立刻被抽到)
        st.session_state['remaining_words'].extend(new_list)
        st.session_state.new_words_input = ""
        st.toast(f"✅ 已添加 {len(new_list)} 个单词到词库！当前剩余待复习: {len(st.session_state['remaining_words'])}")

def check_answer(label):
    st.session_state['user_selection'] = label
    st.session_state['quiz_state'] = 'RESULT'

def next_question():
    st.session_state['quiz_state'] = 'IDLE'
    st.session_state['current_question'] = None
    st.session_state['user_selection'] = None
    st.session_state['generated_image_url'] = None
    generate_new_question()

# def generate_new_question():
#     # 1. 安全检查：总词库是不是空的
#     if not st.session_state['word_bank']:
#         st.warning("词库空了！请先添加单词。")
#         return

#     # 2. 👇 核心逻辑：检查剩余池子是否为空
#     if not st.session_state['remaining_words']:
#         # 如果空了，就重置（开启新一轮）
#         st.session_state['remaining_words'] = st.session_state['word_bank'].copy()
#         st.toast("🔄 所有单词已复习一遍，开启新一轮循环！", icon="🎉")

#     # 清空上一张图
#     st.session_state['generated_image_url'] = None

#     # 3. 👇 从【剩余池子】里抽，而不是从总库里抽
#     target_word = random.choice(st.session_state['remaining_words'])
#     st.session_state['remaining_words'].remove(target_word)

#     api_key = get_api_key()
#     if not api_key:
#         st.warning("请填写 API Key")
#         return
#     # 4. 生成题目文本 (文本生成很快，通常不需要缓存，但其实也可以缓存)
#     # 这里我们只缓存图片，因为图片最慢  且占用流量
#     with st.spinner(f"🤖 Gemini 正在构思【{target_word}】..."):
#         quiz_data = generate_quiz(target_word, api_key)
#     if not quiz_data:
#         st.session_state['current_question'] = quiz_data
#         # 5. 👇 图片缓存逻辑
#         # 检查缓存里有没有这个词的图
#         if target_word in st.session_state['image_cache']:
#             # 命中缓存！直接用，不用等！
#             img_url = st.session_state['image_cache'][target_word]
#             # st.toast(f"⚡️ 命中缓存：{target_word}") # 可选：提示一下用户
#         else:
#             # 没命中，去生成
#             with st.spinner("🎨 正在绘制插图 (新生成)..."):
#                 img_prompt = quiz_data.get("image_gen_prompt", f"illustration of {target_word}")
#                 img_url = generate_image_url(img_prompt)

#                 # 存入缓存！！
#                 st.session_state['image_cache'][target_word] = img_url
#         # 更新当前显示的图片 URL
#         st.session_state['generated_image_url'] = img_url
#         st.session_state['quiz_state'] = 'QUIZ'

def generate_new_question():
    # 1. 安全检查
    if not st.session_state['word_bank']:
        st.warning("词库空了！请先添加单词。")
        return

    # 2. 检查剩余池子
    if not st.session_state['remaining_words']:
        st.session_state['remaining_words'] = st.session_state['word_bank'].copy()
        st.toast("🔄 开启新一轮复习！", icon="🎉")

    st.session_state['generated_image_url'] = None

    # 3. 抽词
    target_word = random.choice(st.session_state['remaining_words'])

    # 先不移除，等成功了再移除，防止报错导致单词丢失
    # st.session_state['remaining_words'].remove(target_word)

    api_key = get_api_key()
    if not api_key:
        st.warning("请填写 API Key")
        return

    # 4. 生成题目文本
    with st.spinner(f"🤖 Gemini 正在构思【{target_word}】..."):
        quiz_data = generate_quiz(target_word, api_key)

    # 🚨 关键修改：如果没有拿到题目数据，直接停止，不往下走！
    if not quiz_data:
        st.error("⚠️ AI 生成题目失败，请重试（可能是网络波动或 Key 额度不足）。")
        return

    # === 只有 quiz_data 存在时，才执行下面的代码 ===

    # 成功了再移除单词
    if target_word in st.session_state['remaining_words']:
        st.session_state['remaining_words'].remove(target_word)

    st.session_state['current_question'] = quiz_data

    # 5. 图片缓存逻辑
    if target_word in st.session_state['image_cache']:
        # 命中缓存
        img_url = st.session_state['image_cache'][target_word]
        st.toast(f"⚡️ 命中缓存：{target_word}")
    else:
        # 没命中，去生成
        with st.spinner("🎨 正在绘制插图..."):
            # 这里如果不缩进，当 quiz_data 为 None 时就会报 AttributeError
            img_prompt = quiz_data.get("image_gen_prompt", f"illustration of {target_word}")
            img_url = generate_image_url(img_prompt)

            # 存入缓存
            st.session_state['image_cache'][target_word] = img_url

    # 更新当前显示的图片 URL
    st.session_state['generated_image_url'] = img_url
    st.session_state['quiz_state'] = 'QUIZ'
# --- 4. 界面渲染 ---

st.title("🎨 英语单词闪卡大师 (Pro Max)")

with st.expander("➕ 添加生词到词库", expanded=(len(st.session_state['word_bank']) == 0)):
    st.text_area("输入单词 (每行一个)", key="new_words_input", height=100)
    st.button("📥 存入词库", on_click=add_words)
# 词库进度显示
if st.session_state['word_bank']:
    total = len(st.session_state['word_bank'])
    left = len(st.session_state['remaining_words'])
    # 显示进度：总共 10 个，本轮还剩 4 个
    st.caption(f"📚 总词库：{total} | ⏳ 本轮剩余：{left}")
    # 甚至可以加个进度条
    st.progress((total - left) / total)
else:
    st.info("👆 请先在上方输入一些单词开始。")

st.divider()

# 出题按钮
if st.session_state['quiz_state'] == 'IDLE' and st.session_state['word_bank']:
    # 动态文案逻辑：如果是第一次，显示“开始”，否则显示“下一张”
    btn_label = "🚀 开始测试" if not st.session_state['has_started'] else "🚀 生成下一张闪卡"
    if st.button(btn_label, type="primary", use_container_width=True):
        st.session_state['has_started'] = True # 只要点了一次，就标记为“已开始”
        generate_new_question()

# 题目显示区
current_q = st.session_state['current_question']
img_url = st.session_state['generated_image_url']

if current_q and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    # 1. 单词与音标
    st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="color: #31333F; margin:0; font-size: 3em;">{current_q['word']}</h1>
        <p style="color: #666; font-size: 1.5em; margin-bottom: 10px;">/{current_q['ipa']}/</p>
    </div>
    """, unsafe_allow_html=True)

    # --- NEW: 语音播放集成 ---
    # 使用 columns 将播放器居中稍微好看一点，或者直接放
    col_audio_1, col_audio_2, col_audio_3 = st.columns([1, 2, 1])
    with col_audio_2:
        try:
            # 实时生成语音流
            tts = gTTS(text=current_q['word'], lang='en')
            sound_file = io.BytesIO()
            tts.write_to_fp(sound_file)
            st.audio(sound_file, format='audio/mp3')
        except Exception as e:
            st.warning("⚠️ 语音生成失败，请检查网络")
    # -----------------------

    # 2. 图片展示 (带重新生成功能)
    if img_url:
        st.image(img_url, caption="AI 联想记忆插图", use_container_width=True)

        # 👇 NEW: 重新生成按钮
        # 只有在做题状态(QUIZ)下才允许重新生成，避免结算后误触
        if st.session_state['quiz_state'] == 'QUIZ':
            col_regen, col_space = st.columns([1, 2])
            with col_regen:
                if st.button("🔄 图片不准？换一张", help="点击重新生成一张新的联想图，并更新缓存"):
                    with st.spinner("🎨 画师正在重绘中..."):
                        # 1. 获取当前的绘图 Prompt
                        img_prompt = current_q.get("image_gen_prompt", f"illustration of {current_q['word']}")

                        # 2. 强制生成新 URL (时间戳不同，图就会变)
                        new_img_url = generate_image_url(img_prompt)

                        # 3. 更新当前显示状态
                        st.session_state['generated_image_url'] = new_img_url

                        # 4. 关键：更新缓存 (覆盖旧图)
                        st.session_state['image_cache'][current_q['word']] = new_img_url

                        # 5. 强制刷新页面，立刻显示新图
                        st.rerun()
    else:
        st.error("图片加载失败")

    # 3. 选项
    st.write("### 👇 选择释义：")
    disable_btns = (st.session_state['quiz_state'] == 'RESULT')
    col1, col2 = st.columns(2, gap="small")
    options = current_q['options']

    with col1:
        for opt in options[:2]:
            btn_type = "secondary"
            if disable_btns:
                if opt['label'] == current_q['correct_label']: btn_type = "primary"
                elif opt['label'] == st.session_state['user_selection']: btn_type = "secondary"
            if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=disable_btns, type=btn_type, use_container_width=True):
                check_answer(opt['label'])
                st.rerun()

    with col2:
        for opt in options[2:]:
            btn_type = "secondary"
            if disable_btns:
                if opt['label'] == current_q['correct_label']: btn_type = "primary"
                elif opt['label'] == st.session_state['user_selection']: btn_type = "secondary"
            if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=disable_btns, type=btn_type, use_container_width=True):
                check_answer(opt['label'])
                st.rerun()

    # 4. 结果
    if st.session_state['quiz_state'] == 'RESULT':
        user_choice = st.session_state['user_selection']
        correct_choice = current_q['correct_label']

        st.divider()
        if user_choice == correct_choice:
            st.success("🎉 正确！")
            st.balloons()
        else:
            correct_text = next((o['text'] for o in options if o['label'] == correct_choice), "未知")
            st.error(f"❌ 错误。答案是 【{correct_choice}】 {correct_text}")
            st.info(f"💡 提示：{current_q.get('visual_cue_cn', '请看图记忆')}")

        st.button("➡️ 下一个", on_click=next_question, type="primary", use_container_width=True)