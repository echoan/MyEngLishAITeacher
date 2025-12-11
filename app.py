import streamlit as st
import google.generativeai as genai
import json
import random
import requests
import time
from gtts import gTTS
import io
import os # 👈 新增：用于检查文件是否存在

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
if 'generated_image_url' not in st.session_state:
    st.session_state['generated_image_url'] = None
if 'has_started' not in st.session_state:
    st.session_state['has_started'] = False
if 'remaining_words' not in st.session_state:
    st.session_state['remaining_words'] = []

# 缓存相关
if 'image_cache' not in st.session_state:
    st.session_state['image_cache'] = {}
if 'quiz_cache' not in st.session_state:
    st.session_state['quiz_cache'] = {}

# 🔥 新增：加载本地预生成的静态图库
if 'static_lib' not in st.session_state:
    st.session_state['static_lib'] = {}
    # 尝试加载 json 文件
    if os.path.exists("static_images.json"):
        try:
            with open("static_images.json", "r", encoding="utf-8") as f:
                st.session_state['static_lib'] = json.load(f)
            # 可以在侧边栏提示一下加载成功
            # st.toast(f"📚 已加载本地图库：{len(st.session_state['static_lib'])} 张")
        except Exception as e:
            print(f"读取图库失败: {e}")

# --- 4. 核心逻辑函数 ---

def generate_image_url(image_prompt):
    timestamp = int(time.time())
    encoded_prompt = requests.utils.quote(image_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?nolog=true&t={timestamp}"

def generate_quiz(word, key):
    genai.configure(api_key=key)
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
            {{"label": "A", "text": "错误意"}},
            {{"label": "B", "text": "正确意"}},
            {{"label": "C", "text": "错误意"}},
            {{"label": "D", "text": "错误意"}}
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
    st.session_state['generated_image_url'] = None
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

    st.session_state['generated_image_url'] = None
    target_word = random.choice(st.session_state['remaining_words'])

    # === 逻辑升级：三级缓存查找 ===

    quiz_data = None
    img_url = None

    # 1. 查内存缓存 (会话级，刷新即逝)
    if target_word in st.session_state['quiz_cache']:
        quiz_data = st.session_state['quiz_cache'][target_word]
    if target_word in st.session_state['image_cache']:
        img_url = st.session_state['image_cache'][target_word]

    # 2. 🔥 查本地图库 (文件级，永久存在)
    # 如果内存里没图，但是静态库里有，直接拿来用！
    if not img_url and target_word in st.session_state['static_lib']:
        img_url = st.session_state['static_lib'][target_word]
        st.session_state['image_cache'][target_word] = img_url # 同步到内存，方便下次更快
        # print(f"🚀 命中本地图库: {target_word}")

    # 3. 还没图？那就现场生成 (Fallback)
    if not quiz_data:
        with st.spinner(f"🤖 AI 正在构思 {target_word}..."):
            quiz_data = generate_quiz(target_word, api_key)
            if quiz_data:
                st.session_state['quiz_cache'][target_word] = quiz_data
            else:
                return

    if not img_url and quiz_data:
        # 使用 Gemma 生成的详细 Prompt
        p = quiz_data.get("image_gen_prompt", f"illustration of {target_word}")
        img_url = generate_image_url(p)
        st.session_state['image_cache'][target_word] = img_url

    # 4. 更新界面
    if target_word in st.session_state['remaining_words']:
        st.session_state['remaining_words'].remove(target_word)

    st.session_state['current_question'] = quiz_data
    st.session_state['generated_image_url'] = img_url
    st.session_state['quiz_state'] = 'QUIZ'

    # st.rerun()

# --- 5. 界面渲染 ---

st.title("🎨 英语单词闪卡 (图库加速版)")

# 显示图库状态
lib_size = len(st.session_state.get('static_lib', {}))
if lib_size > 0:
    st.sidebar.success(f"📦 已加载本地图库: {lib_size} 词")

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
        st.rerun() # 👈 在这里加上这行！

current_q = st.session_state['current_question']
img_url = st.session_state['generated_image_url']

if current_q and st.session_state['quiz_state'] in ['QUIZ', 'RESULT']:
    st.markdown(f"<h1 style='text-align: center;'>{current_q['word']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>/{current_q['ipa']}/</p>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        try:
            tts = gTTS(text=current_q['word'], lang='en')
            sound_file = io.BytesIO()
            tts.write_to_fp(sound_file)
            st.audio(sound_file, format='audio/mp3')
        except: pass

    if img_url:
        # 这里会直接用 URL 加载，如果 URL 在 static_images.json 里，
        # 且之前浏览器访问过，浏览器甚至会直接从 Disk Cache 读取，速度极快
        st.image(img_url, caption="联想记忆", use_container_width=True)

        if st.session_state['quiz_state'] == 'QUIZ':
            if st.button("🔄 图片不准？重画"):
                with st.spinner("重绘中..."):
                    p = current_q.get("image_gen_prompt", f"illustration of {current_q['word']}")
                    new_url = generate_image_url(p)
                    time.sleep(0.5)
                    st.session_state['generated_image_url'] = new_url
                    st.session_state['image_cache'][current_q['word']] = new_url
                    st.rerun()

    st.write("### 👇 选择释义：")
    dis = (st.session_state['quiz_state'] == 'RESULT')
    options = current_q['options']

    col1, col2 = st.columns(2)
    def render_btn(idx):
        if idx >= len(options): return
        opt = options[idx]
        b_type = "primary" if dis and opt['label'] == current_q['correct_label'] else "secondary"
        if st.button(f"{opt['label']}. {opt['text']}", key=opt['label'], disabled=dis, type=b_type, use_container_width=True):
            check_answer(opt['label'])
            st.rerun()

    with col1: render_btn(0); render_btn(1)
    with col2: render_btn(2); render_btn(3)

    if st.session_state['quiz_state'] == 'RESULT':
        if st.session_state['user_selection'] == current_q['correct_label']:
            st.success("🎉 正确！")
        else:
            ans = next((o['text'] for o in options if o['label'] == current_q['correct_label']), "")
            st.error(f"❌ 错误。答案是 {current_q['correct_label']}. {ans}")
            st.info(f"💡 提示：{current_q.get('visual_cue_cn', '')}")
        st.button("➡️ 下一个", on_click=next_question, type="primary", use_container_width=True)