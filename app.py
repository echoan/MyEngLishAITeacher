'''
Author: Chengya
Description: Description
Date: 2025-12-10 20:44:40
LastEditors: Chengya
LastEditTime: 2025-12-10 20:50:33
'''
import streamlit as st
import google.generativeai as genai
import json
import random
import requests
import time
from gtts import gTTS
import io

# --- 1. 页面配置 ---
st.set_page_config(page_title="英语单词闪卡大师 (Pro Max)", page_icon="🎨")

# --- 2. 侧边栏：优先渲染 (确保一进来就能看到输入框) ---
with st.sidebar:
    st.header("🔑 API 配置")
    # 将 api_key 定义在全局，方便后续调用
    api_key = st.text_input(
        "请输入 Gemini API Key",
        type="password",
        placeholder="AIzaSy...",
        help="您的 Key 仅用于当前会话调用 Google API，不会被存储。"
    )
    st.caption("还没有 Key？[👉 免费获取](https://aistudio.google.com/app/apikey)")
    if not api_key:
        st.warning("👈 请先在左侧输入 Key")

# --- 3. 状态初始化 ---
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
if 'has_started' not in st.session_state:
    st.session_state['has_started'] = False
if 'remaining_words' not in st.session_state:
    st.session_state['remaining_words'] = []
if 'image_cache' not in st.session_state:
    st.session_state['image_cache'] = {}

# --- 4. 核心逻辑函数 ---

def generate_image_url(image_prompt):
    timestamp = int(time.time())
    encoded_prompt = requests.utils.quote(image_prompt)
    # 使用 Pollinations 生成图片
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&t={timestamp}"
    return image_url

def generate_quiz(word, key):
    genai.configure(api_key=key)

    # 🔥 关键修改：使用标准版 1.5 Flash (新账号稳稳的)
    model = genai.GenerativeModel('gemini-2.5-flash')

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
        st.session_state['word_bank'].extend(new_list)
        st.session_state['remaining_words'].extend(new_list)
        st.session_state.new_words_input = ""
        st.toast(f"✅ 已添加 {len(new_list)} 个单词！待复习: {len(st.session_state['remaining_words'])}")

def check_answer(label):
    st.session_state['user_selection'] = label
    st.session_state['quiz_state'] = 'RESULT'

def next_question():
    st.session_state['quiz_state'] = 'IDLE'
    st.session_state['current_question'] = None
    st.session_state['user_selection'] = None
    st.session_state['generated_image_url'] = None
    generate_new_question()

def generate_new_question():
    # 1. 检查 Key 是否存在 (从全局变量获取)
    if not api_key:
        st.toast("⚠️ 请先在左侧输入 API Key")
        return

    # 2. 安全检查
    if not st.session_state['word_bank']:
        st.warning("词库空了！请先添加单词。")
        return

    # 3. 检查剩余池子 (洗牌)
    if not st.session_state['remaining_words']:
        st.session_state['remaining_words'] = st.session_state['word_bank'].copy()
        st.toast("🔄 开启新一轮复习！", icon="🎉")

    st.session_state['generated_image_url'] = None

    # 4. 抽词
    target_word = random.choice(st.session_state['remaining_words'])

    # 5. 生成文本
    with st.spinner(f"🤖 Gemini 正在构思【{target_word}】..."):
        # 传入全局的 api_key
        quiz_data = generate_quiz(target_word, api_key)

    if not quiz_data:
        # 错误已在 generate_quiz 中显示，这里直接返回
        return

    # 成功后再移除单词
    if target_word in st.session_state['remaining_words']:
        st.session_state['remaining_words'].remove(target_word)

    st.session_state['current_question'] = quiz_data

    # 6. 图片缓存逻辑
    if target_word in st.session_state['image_cache']:
        img_url = st.session_state['image_cache'][target_word]
        st.toast(f"⚡️ 命中图片缓存：{target_word}")
    else:
        with st.spinner("🎨 正在绘制插图..."):
            img_prompt = quiz_data.get("image_gen_prompt", f"illustration of {target_word}")
            img_url = generate_image_url(img_prompt)
            st.session_state['image_cache'][target_word] = img_url

    st.session_state['generated_image_url'] = img_url
    st.session_state['quiz_state'] = 'QUIZ'

# --- 5. 界面渲染 ---

st.title("🎨 英语单词闪卡大师 (Pro Max)")

with st.expander("➕ 添加生词到词库", expanded=(len(st.session_state['word_bank']) == 0)):
    st.text_area("输入单词 (每行一个)", key="new_words_input", height=100)
    st.button("📥 存入词库", on_click=add_words)

if st.session_state['word_bank']:
    total = len(st.session_state['word_bank'])
    left = len(st.session_state['remaining_words'])
    st.caption(f"📚 总词库：{total} | ⏳ 本轮剩余：{left}")
    st.progress((total - left) / total if total > 0 else 0)
else:
    st.info("👆 请先在上方输入一些单词开始。")

st.divider()

# 出题按钮
if st.session_state['quiz_state'] == 'IDLE' and st.session_state['word_bank']:
    btn_label = "🚀 开始测试" if not st.session_state['has_started'] else "🚀 生成下一张闪卡"
    # 如果没填 Key，禁用按钮
    if st.button(btn_label, type="primary", use_container_width=True, disabled=(not api_key)):
        st.session_state['has_started'] = True
        generate_new_question()

# 题目显示区
current_q = st.session_state['current_question']
img_url = st.session_state['generated_image_url']

if current_q and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    # 单词卡片
    st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="color: #31333F; margin:0; font-size: 3em;">{current_q['word']}</h1>
        <p style="color: #666; font-size: 1.5em; margin-bottom: 10px;">/{current_q['ipa']}/</p>
    </div>
    """, unsafe_allow_html=True)

    # 语音播放
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        try:
            tts = gTTS(text=current_q['word'], lang='en')
            sound_file = io.BytesIO()
            tts.write_to_fp(sound_file)
            st.audio(sound_file, format='audio/mp3')
        except Exception:
            st.warning("⚠️ 语音暂不可用")

    # 图片展示
    if img_url:
        st.image(img_url, caption="AI 联想记忆插图", use_container_width=True)

        # 重新生成按钮 (仅在答题时显示)
        if st.session_state['quiz_state'] == 'QUIZ':
            col_regen, _ = st.columns([1, 2])
            with col_regen:
                if st.button("🔄 图片不准？换一张"):
                    with st.spinner("🎨 重绘中..."):
                        prompt = current_q.get("image_gen_prompt", f"illustration of {current_q['word']}")
                        new_url = generate_image_url(prompt)
                        st.session_state['generated_image_url'] = new_url
                        st.session_state['image_cache'][current_q['word']] = new_url
                        st.rerun()

    # 选项区
    st.write("### 👇 选择释义：")
    disable_btns = (st.session_state['quiz_state'] == 'RESULT')
    options = current_q['options']

    col1, col2 = st.columns(2, gap="small")

    # 辅助函数：渲染按钮
    def render_option_btn(idx):
        opt = options[idx]
        btn_type = "secondary"
        if disable_btns:
            if opt['label'] == current_q['correct_label']: btn_type = "primary"
            elif opt['label'] == st.session_state['user_selection']: btn_type = "secondary"

        if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=disable_btns, type=btn_type, use_container_width=True):
            check_answer(opt['label'])
            st.rerun()

    with col1:
        render_option_btn(0) # A
        render_option_btn(1) # B
    with col2:
        render_option_btn(2) # C
        render_option_btn(3) # D

    # 结果反馈
    if st.session_state['quiz_state'] == 'RESULT':
        user_choice = st.session_state['user_selection']
        correct_choice = current_q['correct_label']

        st.divider()
        if user_choice == correct_choice:
            st.success("🎉 正确！")
            st.balloons()
        else:
            # 找到正确文本
            ans_text = next((o['text'] for o in options if o['label'] == correct_choice), "")
            st.error(f"❌ 错误。正确答案是 【{correct_choice}】 {ans_text}")
            st.info(f"💡 记忆提示：{current_q.get('visual_cue_cn', '暂无提示')}")

        st.button("➡️ 下一个", on_click=next_question, type="primary", use_container_width=True)