'''
Author: Chengya
Description: Description
Date: 2025-12-09 11:13:42
LastEditors: Chengya
LastEditTime: 2025-12-09 11:13:43
'''
import streamlit as st
import google.generativeai as genai
import json
import random

# --- 1. 页面配置 ---
st.set_page_config(page_title="英语单词闪卡大师", page_icon="🎓")

# --- 2. 状态初始化 (State Management) ---
if 'word_bank' not in st.session_state:
    st.session_state['word_bank'] = []  # 缓存单词库
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = None # 当前题目数据
if 'quiz_state' not in st.session_state:
    st.session_state['quiz_state'] = 'IDLE' # 状态机: IDLE, QUIZ, RESULT
if 'user_selection' not in st.session_state:
    st.session_state['user_selection'] = None

# --- 3. 核心逻辑函数 ---

# 获取 API Key (优先从 Secrets 读取)
def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    return st.sidebar.text_input("请输入 Google Gemini API Key", type="password")

# 调用 AI 生成题目 (强制 JSON 格式)
def generate_quiz(word, api_key):
    genai.configure(api_key=api_key)
    # 使用最新的 Flash 模型
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    请针对单词 "{word}" 设计一道英语词汇测试题。
    请严格输出标准的 JSON 格式，不要包含 Markdown 标记（如 ```json）。

    JSON 数据结构如下：
    {{
        "word": "{word}",
        "ipa": "单词音标",
        "visual_cue": "描述一个生动的联想记忆场景（100字以内，中文）",
        "options": [
            {{"label": "A", "text": "错误中文释义1"}},
            {{"label": "B", "text": "正确中文释义"}},
            {{"label": "C", "text": "错误中文释义2"}},
            {{"label": "D", "text": "错误中文释义3"}}
        ],
        "correct_label": "B" (必须对应上面正确的选项 Label)
    }}
    注意：请随机打乱正确选项的位置，不要总是 B。
    """

    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI 生成解析失败: {e}")
        return None

# 添加单词到缓存的回调函数
def add_words():
    raw_text = st.session_state.new_words_input
    if raw_text.strip():
        # 分割并去重
        new_list = [w.strip() for w in raw_text.split('\n') if w.strip()]
        st.session_state['word_bank'].extend(new_list)
        # 清空输入框 (Streamlit 特性: 修改绑定的 key 对应的值)
        st.session_state.new_words_input = ""
        st.toast(f"✅ 已添加 {len(new_list)} 个单词到词库！")

# 选择答案的回调函数
def check_answer(label):
    st.session_state['user_selection'] = label
    st.session_state['quiz_state'] = 'RESULT'

# 下一题的回调函数
def next_question():
    st.session_state['quiz_state'] = 'IDLE'
    st.session_state['current_question'] = None
    st.session_state['user_selection'] = None
    generate_new_question()

# 生成新题目的逻辑
def generate_new_question():
    if not st.session_state['word_bank']:
        st.warning("词库空了！请先添加单词。")
        return

    # 1. 随机抽词
    target_word = random.choice(st.session_state['word_bank'])

    # 2. 调用 API
    api_key = get_api_key()
    if not api_key:
        st.warning("请填写 API Key")
        return

    with st.spinner(f"正在为【{target_word}】生成闪卡..."):
        quiz_data = generate_quiz(target_word, api_key)
        if quiz_data:
            st.session_state['current_question'] = quiz_data
            st.session_state['quiz_state'] = 'QUIZ'

# --- 4. 界面渲染 ---

st.title("🎓 英语单词闪卡应用 (Pro版)")

# --- 区域 A: 单词录入区 ---
with st.expander("➕ 添加生词到词库", expanded=(len(st.session_state['word_bank']) == 0)):
    st.text_area(
        "输入单词 (每行一个)",
        key="new_words_input",
        height=100,
        help="输入后点击下方按钮，输入框会自动清空，单词会存入缓存。"
    )
    st.button("📥 存入词库", on_click=add_words)

# 显示当前词库状态
if st.session_state['word_bank']:
    st.caption(f"📚 当前词库缓存：{len(st.session_state['word_bank'])} 个单词")
else:
    st.info("👆 请先在上方输入一些单词开始。")

st.divider()

# --- 区域 B: 出题控制区 ---
# 如果没有题，且词库有词，显示“开始测试”按钮
if st.session_state['quiz_state'] == 'IDLE' and st.session_state['word_bank']:
    if st.button("🚀 随机抽取一个单词测试", type="primary"):
        generate_new_question()

# --- 区域 C: 题目显示区 ---
current_q = st.session_state['current_question']

if current_q and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    # 1. 显示卡片头部
    st.markdown(f"""
    <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; text-align: center; margin-bottom: 20px;">
        <h1 style="color: #31333F; margin:0;">{current_q['word']}</h1>
        <p style="color: #666; font-size: 1.2em; margin-top: 5px;">/{current_q['ipa']}/</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. 显示记忆场景
    st.info(f"🧠 **联想记忆**：{current_q['visual_cue']}")

    # 3. 显示选项 (使用列布局模拟按钮组)
    st.write("#### 请选择正确的中文释义：")

    # 如果已经选了结果，就禁用按钮
    disable_btns = (st.session_state['quiz_state'] == 'RESULT')

    col1, col2 = st.columns(2)
    options = current_q['options']

    # 渲染 A/B 按钮
    with col1:
        for opt in options[:2]:
            if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=disable_btns, use_container_width=True):
                check_answer(opt['label'])
                st.rerun() # 强制刷新以显示结果

    # 渲染 C/D 按钮
    with col2:
        for opt in options[2:]:
            if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=disable_btns, use_container_width=True):
                check_answer(opt['label'])
                st.rerun()

    # 4. 结果反馈区
    if st.session_state['quiz_state'] == 'RESULT':
        user_choice = st.session_state['user_selection']
        correct_choice = current_q['correct_label']

        if user_choice == correct_choice:
            st.success("🎉 回答正确！太棒了！")
            st.balloons()
        else:
            # 找到正确选项的文本
            correct_text = next((o['text'] for o in options if o['label'] == correct_choice), "未知")
            st.error(f"❌ 回答错误。正确答案是：{correct_choice}. {correct_text}")

        # 显示“下一题”按钮
        st.button("➡️ 下一个单词", on_click=next_question, type="primary")