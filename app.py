'''
Author: Chengya
Description: Description
Date: 2025-12-09 11:29:32
LastEditors: Chengya
LastEditTime: 2025-12-09 11:29:33
'''
import streamlit as st
import google.generativeai as genai
import json
import random
import requests # 需要导入 requests 来调用绘图 API
import time # 用于生成时间戳防缓存

# --- 1. 页面配置 ---
st.set_page_config(page_title="英语单词闪卡大师 (AI绘图版)", page_icon="🎨")

# --- 2. 状态初始化 ---
if 'word_bank' not in st.session_state:
    st.session_state['word_bank'] = []
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = None
if 'quiz_state' not in st.session_state:
    st.session_state['quiz_state'] = 'IDLE'
if 'user_selection' not in st.session_state:
    st.session_state['user_selection'] = None
if 'generated_image_url' not in st.session_state: # 新增：存图片URL
    st.session_state['generated_image_url'] = None

# --- 3. 核心逻辑函数 ---

def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    return st.sidebar.text_input("请输入 Google Gemini API Key", type="password")

# NEW: 调用第三方免费 API 生成图片
def generate_image_url(image_prompt):
    # 使用 Pollinations.ai 免费 API (无需 Key, 速度快)
    # 为了防止图片缓存，加一个时间戳
    timestamp = int(time.time())
    # 对 prompt 进行 URL 编码
    encoded_prompt = requests.utils.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&t={timestamp}"
    return image_url

# 修改 Prompt，让 AI 生成英文绘图指令
def generate_quiz(word, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    请针对单词 "{word}" 设计一道英语词汇测试题。

    核心任务：
    1. 为这个单词设计一个非常有创意、画面感极强、有助于记忆的场景。
    2. 将这个场景翻译成一段详细的【英文绘图提示词 (Image Generation Prompt)】。
    3. 英文提示词要求：包含主体、动作、环境、光线、艺术风格（如 cartoon style, digital art, vibrant colors）。例如： "A cute cartoon squirrel holding a giant acorn, standing on a pile of books in a magical forest library, glowing warm light, digital illustration."

    请严格输出标准的 JSON 格式，不要包含 Markdown 标记。
    JSON 结构如下：
    {{
        "word": "{word}",
        "ipa": "单词音标",
        # 这里改为英文绘图 Prompt
        "image_gen_prompt": "Detailed English image generation prompt describing the memory scene...",
        # 保留一个简短的中文描述用于备用显示
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
        st.session_state.new_words_input = ""
        st.toast(f"✅ 已添加 {len(new_list)} 个单词到词库！")

def check_answer(label):
    st.session_state['user_selection'] = label
    st.session_state['quiz_state'] = 'RESULT'

def next_question():
    st.session_state['quiz_state'] = 'IDLE'
    st.session_state['current_question'] = None
    st.session_state['user_selection'] = None
    # 清空图片
    st.session_state['generated_image_url'] = None
    generate_new_question()

def generate_new_question():
    if not st.session_state['word_bank']:
        st.warning("词库空了！请先添加单词。")
        return

    st.session_state['generated_image_url'] = None # 先清空上一张图

    target_word = random.choice(st.session_state['word_bank'])
    api_key = get_api_key()
    if not api_key:
        st.warning("请填写 API Key")
        return

    # 1. 生成文本数据
    with st.spinner(f"🤖 Gemini 正在构思【{target_word}】的记忆场景..."):
        quiz_data = generate_quiz(target_word, api_key)

    if quiz_data:
        # 2. 拿着 Gemini 的描述去生成图片
        with st.spinner("🎨 AI 画师正在绘制插图 (可能需要 5-10 秒)..."):
            # 获取英文 Prompt
            img_prompt = quiz_data.get("image_gen_prompt", f"A creative illustration representing the word {target_word}")
            # 生成 URL
            img_url = generate_image_url(img_prompt)
            # 存入状态
            st.session_state['current_question'] = quiz_data
            st.session_state['generated_image_url'] = img_url
            st.session_state['quiz_state'] = 'QUIZ'

# --- 4. 界面渲染 ---

st.title("🎨 英语单词闪卡大师 (AI绘图版)")

# --- 区域 A: 单词录入区 ---
with st.expander("➕ 添加生词到词库", expanded=(len(st.session_state['word_bank']) == 0)):
    st.text_area("输入单词 (每行一个)", key="new_words_input", height=100)
    st.button("📥 存入词库", on_click=add_words)

if st.session_state['word_bank']:
    st.caption(f"📚 当前词库缓存：{len(st.session_state['word_bank'])} 个单词")
else:
    st.info("👆 请先在上方输入一些单词开始。")

st.divider()

# --- 区域 B: 出题控制区 ---
if st.session_state['quiz_state'] == 'IDLE' and st.session_state['word_bank']:
    if st.button("🚀 生成下一张闪卡", type="primary"):
        generate_new_question()

# --- 区域 C: 题目显示区 ---
current_q = st.session_state['current_question']
img_url = st.session_state['generated_image_url']

if current_q and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    # 1. 单词卡片头
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; text-align: center; margin-bottom: 20px;">
        <h1 style="color: #31333F; margin:0; font-size: 3em;">{current_q['word']}</h1>
        <p style="color: #666; font-size: 1.5em; margin-top: 10px;">/{current_q['ipa']}/</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. 显示 AI 插图 (核心新功能!)
    if img_url:
        with st.container():
            # 使用 columns 居中显示图片
            col_spacer1, col_img, col_spacer2 = st.columns([1, 3, 1])
            with col_img:
                st.image(img_url, caption="AI 联想记忆插图", use_container_width=True)
                # 可以选择显示中文提示辅助
                # st.caption(f"💡 提示: {current_q.get('visual_cue_cn', '')}")
    else:
        st.error("图片加载失败，请刷新重试。")

    # 3. 选项区
    st.write("### 👇 选择正确的中文释义：")

    disable_btns = (st.session_state['quiz_state'] == 'RESULT')
    col1, col2 = st.columns(2, gap="medium")
    options = current_q['options']

    with col1:
        for opt in options[:2]:
            btn_type = "secondary"
            # 结果展示时高亮正确/错误
            if disable_btns:
                if opt['label'] == current_q['correct_label']: btn_type = "primary" # 正确标绿(Streamlit primary色)
                elif opt['label'] == st.session_state['user_selection']: btn_type = "secondary" # 选错的标灰

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

    # 4. 结果反馈区
    if st.session_state['quiz_state'] == 'RESULT':
        user_choice = st.session_state['user_selection']
        correct_choice = current_q['correct_label']

        st.divider()
        if user_choice == correct_choice:
            st.success(f"🎉 回答正确！这张图完美诠释了 {current_q['word']}！")
            st.balloons()
        else:
            correct_text = next((o['text'] for o in options if o['label'] == correct_choice), "未知")
            st.error(f"❌ 回答错误。正确答案是 【{correct_choice}】 {correct_text}。")
            st.info(f"💡 记忆提示：{current_q.get('visual_cue_cn', '请参考上方插图')}")

        st.button("➡️ 下一个单词", on_click=next_question, type="primary", use_container_width=True)