'''
Author: Chengya
Description: Description
Date: 2025-12-08 17:40:02
LastEditors: Chengya
LastEditTime: 2025-12-09 10:21:20
'''
import streamlit as st
import google.generativeai as genai
import json

# --- 1. 配置页面 ---
st.set_page_config(page_title="英语单词闪卡大师", page_icon="🎓")

# --- 2. 侧边栏：输入 API Key (为了安全，让用户或你自己填) ---
with st.sidebar:
    st.header("设置")
    api_key = st.text_input("请输入 Google Gemini API Key", type="password")
    st.markdown("[如何获取 API Key?](https://aistudio.google.com/app/apikey)")

# --- 3. 核心逻辑：定义 AI 模型 ---
def get_gemini_response(prompt):
    if not api_key:
        return "请先在左侧输入API Key"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('modules/gemini-1.5-flash') # 使用速度较快的 Flash 模型
        response = model.generate_content(prompt)
        if response.text:
           return response.text
        else:
           return "AI 未返回有效内容，请稍后重试。"
    except Exception as e:
        return f"调用 AI 出错: {str(e)}"

# --- 4. 界面布局 ---
st.title("🎓 英语单词闪卡应用 (AI版)")
st.markdown("输入单词列表，AI 为你生成带场景记忆的测试题！")

# 状态管理：保存单词和当前的题目
if 'quiz_data' not in st.session_state:
    st.session_state['quiz_data'] = ""

# --- 5. 区域 A: 输入单词 ---
with st.expander("📝 第一步：导入单词 (点击展开)", expanded=True):
    user_words = st.text_area("请粘贴你的单词列表 (每行一个):", "negotiate\nambitious\nconsensus")

    if st.button("生成闪卡测试"):
        # 这里我们将 Prompt 包装好发送给 AI
        full_prompt = f"""
        你是一个英语单词闪卡应用。
        请从以下单词列表中随机选择一个：
        {user_words}

        请严格按照以下格式返回内容（不要多余的废话）：

        单词: [Target Word]
        音标: [IPA]
        记忆场景: [描述一个生动的画面来辅助记忆]
        问题: [这个单词的中文意思?]
        选项A: [错误选项]
        选项B: [正确选项]
        选项C: [错误选项]
        选项D: [错误选项]
        正确答案: [A/B/C/D]
        """

        with st.spinner("AI 正在出题中..."):
            result = get_gemini_response(full_prompt)
            st.session_state['quiz_data'] = result # 存入缓存

# --- 6. 区域 B: 显示题目卡片 ---
if st.session_state['quiz_data']:
    st.divider()
    st.subheader("💡 单词记忆卡")

    # 简单的文本处理，实际开发可以用 JSON 格式让排版更漂亮
    st.info(st.session_state['quiz_data'])

    st.button("下一个单词", on_click=lambda: st.session_state.pop('quiz_data', None))