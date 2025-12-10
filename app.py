import streamlit as st
import google.generativeai as genai
import json
import random
import requests
import time
from gtts import gTTS
import io
import concurrent.futures

# --- 1. 页面配置 ---
st.set_page_config(page_title="英语单词闪卡大师 (极速版)", page_icon="⚡️")

# --- 2. 侧边栏 ---
with st.sidebar:
    st.header("🔑 API 配置")
    api_key = st.text_input(
        "请输入 Gemini API Key",
        type="password",
        help="建议使用支持 Gemma 3 的新账号 Key"
    )
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
if 'generated_image_data' not in st.session_state:
    st.session_state['generated_image_data'] = None
if 'has_started' not in st.session_state:
    st.session_state['has_started'] = False
if 'remaining_words' not in st.session_state:
    st.session_state['remaining_words'] = []
if 'image_cache' not in st.session_state:
    st.session_state['image_cache'] = {}
if 'quiz_cache' not in st.session_state:
    st.session_state['quiz_cache'] = {}

# --- 4. 核心逻辑函数 ---

def generate_image_url(image_prompt):
    timestamp = int(time.time())
    encoded_prompt = requests.utils.quote(image_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&t={timestamp}"

# 后端下载图片函数 (带伪装头)
def fetch_image_data(prompt, timeout=3.5):
    url = generate_image_url(prompt)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.content
        else:
            print(f"❌ 图片接口错误: {resp.status_code}")
    except Exception as e:
        print(f"❌ 图片下载异常: {e}")
    return None

def generate_quiz(word, key):
    genai.configure(api_key=key)
    # 使用 Gemma 3 (14.4K 配额)
    model = genai.GenerativeModel('models/gemma-3-27b-it')

    prompt = f"""
    请针对单词 "{word}" 设计一道英语词汇测试题。

    必须严格遵守以下规则：
    1. 直接返回纯 JSON 格式，不要使用 Markdown 标记。
    2. **核心要求：选项 (options) 中的 text 必须是该单词的【中文释义】，绝对不要使用英文解释！**
    3. 干扰项 (错误选项) 也必须是其他不相关的【中文词汇】。

    JSON 结构示例：
    {{
        "word": "{word}",
        "ipa": "音标",
        "image_gen_prompt": "Cartoon style illustration of...",
        "visual_cue_cn": "中文场景描述",
        "options": [
            {{"label": "A", "text": "错误的中文意思"}},
            {{"label": "B", "text": "正确的中文意思"}},
            {{"label": "C", "text": "错误的中文意思"}},
            {{"label": "D", "text": "错误的中文意思"}}
        ],
        "correct_label": "B"
    }}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```json" in text:
            text = text.replace("```json", "").replace("```", "")
        if "```" in text:
            text = text.replace("```", "")
        return json.loads(text)
    except Exception as e:
        print(f"Gemma Error: {e}")
        return None

def add_words():
    raw_text = st.session_state.new_words_input
    if raw_text.strip():
        new_list = [w.strip() for w in raw_text.split('\n') if w.strip()]
        st.session_state['word_bank'].extend(new_list)
        st.session_state['remaining_words'].extend(new_list)
        st.session_state.new_words_input = ""
        st.toast(f"✅ 已添加 {len(new_list)} 个单词")

def check_answer(label):
    st.session_state['user_selection'] = label
    st.session_state['quiz_state'] = 'RESULT'

def next_question():
    st.session_state['quiz_state'] = 'IDLE'
    st.session_state['current_question'] = None
    st.session_state['user_selection'] = None
    st.session_state['generated_image_data'] = None
    generate_new_question()

def generate_new_question():
    if not api_key:
        st.toast("⚠️ 请先输入 API Key")
        return

    if not st.session_state['remaining_words']:
        if not st.session_state['word_bank']:
            st.warning("词库空了！")
            return
        st.session_state['remaining_words'] = st.session_state['word_bank'].copy()
        st.toast("🔄 开启新一轮复习！")

    st.session_state['generated_image_data'] = None
    target_word = random.choice(st.session_state['remaining_words'])

    # === 并行逻辑 ===
    quiz_data = None
    img_data = None

    # 查缓存
    if target_word in st.session_state['quiz_cache']:
        quiz_data = st.session_state['quiz_cache'][target_word]
    if target_word in st.session_state['image_cache']:
        img_data = st.session_state['image_cache'][target_word]
        st.toast("⚡️ 命中缓存")

    missing_text = (quiz_data is None)
    missing_img = (img_data is None)

    if missing_text or missing_img:
        with st.spinner(f"🚀 AI 正在极速出题: {target_word}..."):
            local_img_prompt = f"Creative cartoon illustration of '{target_word}', vector art style, white background, vivid colors."

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_text = None
                future_img = None

                if missing_text:
                    future_text = executor.submit(generate_quiz, target_word, api_key)
                if missing_img:
                    future_img = executor.submit(fetch_image_data, local_img_prompt, 3.5)

                if future_text:
                    try:
                        quiz_data = future_text.result()
                        if quiz_data:
                            st.session_state['quiz_cache'][target_word] = quiz_data
                    except Exception:
                        st.error("AI 出题失败")
                        return

                if future_img:
                    try:
                        img_data = future_img.result(timeout=4)
                        if img_data:
                            st.session_state['image_cache'][target_word] = img_data
                        else:
                            print(f"图片下载失败或超时: {target_word}")
                    except concurrent.futures.TimeoutError:
                        print("图片线程超时 - 跳过")
                        img_data = None

    if not quiz_data: return

    if target_word in st.session_state['remaining_words']:
        st.session_state['remaining_words'].remove(target_word)

    st.session_state['current_question'] = quiz_data
    st.session_state['generated_image_data'] = img_data
    st.session_state['quiz_state'] = 'QUIZ'
    st.rerun()

# --- 5. 界面渲染 ---
st.title("⚡️ 英语单词闪卡 (Gemma 3 并行版)")

with st.expander("➕ 添加生词", expanded=not st.session_state['word_bank']):
    st.text_area("输入单词 (每行一个)", key="new_words_input", height=100)
    st.button("存入", on_click=add_words)

if st.session_state['word_bank']:
    left = len(st.session_state['remaining_words'])
    st.caption(f"待复习: {left} / 总数: {len(st.session_state['word_bank'])}")
    st.progress(1 - left/len(st.session_state['word_bank']))

st.divider()

if st.session_state['quiz_state'] == 'IDLE' and st.session_state['word_bank']:
    btn_label = "🚀 开始测试" if not st.session_state['has_started'] else "🚀 下一张"
    if st.button(btn_label, type="primary", use_container_width=True, disabled=not api_key):
        st.session_state['has_started'] = True
        generate_new_question()

curr = st.session_state['current_question']
img_data = st.session_state['generated_image_data']

if curr and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    st.markdown(f"<h1 style='text-align: center;'>{curr['word']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>/{curr['ipa']}/</p>", unsafe_allow_html=True)

    # 语音
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        try:
            tts = gTTS(text=curr['word'], lang='en')
            sound_file = io.BytesIO()
            tts.write_to_fp(sound_file)
            st.audio(sound_file, format='audio/mp3')
        except: pass

    # 图片展示区
    img_container = st.empty()

    if img_data:
        img_container.image(img_data, caption="AI 联想记忆", use_container_width=True)
    else:
        img_container.warning("🐢 图片加载失败 (可能网络超时)，点击下方按钮重试 👇")

    # 重新生成按钮 (任何时候都显示)
    if st.session_state['quiz_state'] == 'QUIZ':
        regen_label = "🔄 图片不准？重画" if img_data else "🔄 重新加载图片"
        if st.button(regen_label, help="点击重新调用 AI 绘图"):
            with st.spinner("🎨 正在努力重绘中..."):
                p = curr.get("image_gen_prompt", f"illustration of {curr['word']}")
                # 手动重试给 10秒
                new_img = fetch_image_data(p, timeout=10)
                if new_img:
                    st.session_state['generated_image_data'] = new_img
                    st.session_state['image_cache'][curr['word']] = new_img
                    st.rerun()
                else:
                    st.toast("❌ 重试依然失败，请检查网络")

    # 选项区
    st.write("### 👇 选择释义：")
    dis = (st.session_state['quiz_state'] == 'RESULT')
    options = curr['options']

    col1, col2 = st.columns(2)
    def render_btn(idx):
        if idx >= len(options): return
        opt = options[idx]
        b_type = "primary" if dis and opt['label'] == curr['correct_label'] else "secondary"
        if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=dis, type=b_type, use_container_width=True):
            check_answer(opt['label'])
            st.rerun()

    with col1: render_btn(0); render_btn(1)
    with col2: render_btn(2); render_btn(3)

    if st.session_state['quiz_state'] == 'RESULT':
        if st.session_state['user_selection'] == curr['correct_label']:
            st.success("🎉 正确！")
        else:
            ans = next((o['text'] for o in options if o['label'] == curr['correct_label']), "")
            st.error(f"❌ 错误。答案是 {curr['correct_label']}. {ans}")
            st.info(f"💡 提示：{curr.get('visual_cue_cn', '')}")
        st.button("➡️ 下一个", on_click=next_question, type="primary", use_container_width=True)