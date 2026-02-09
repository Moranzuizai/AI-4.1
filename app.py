import streamlit as st
import pandas as pd
import os
import json
import datetime
import streamlit.components.v1 as components
import qianfan
from io import BytesIO

# ==========================================
# 1. 核心配置与日志系统
# ==========================================
CONFIG_FILE = "config_setting.json"
LOG_FILE = "access_history.csv"

def load_config():
    default_config = {
        "admin_password": "199266", 
        "user_password": "a123456",
        "baidu_api_key": "",
        "baidu_secret_key": "",
        "upload_hint": "⬆️ 请上传班级教学数据 Excel 原文件",
        "app_title": "AI 课堂智能分析工作站"
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f: json.dump(default_config, f)
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        for k,v in default_config.items():
            if k not in config: config[k] = v
        return config

def save_config(c):
    with open(CONFIG_FILE, 'w') as f: json.dump(c, f)

def add_log(role):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = pd.DataFrame([[now, role]], columns=["时间", "登录角色"])
    if not os.path.exists(LOG_FILE):
        log_data.to_csv(LOG_FILE, index=False)
    else:
        log_data.to_csv(LOG_FILE, mode='a', header=False, index=False)

conf = load_config()
st.set_page_config(page_title=conf["app_title"], layout="wide")

# 初始化状态
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'ai_chat_history' not in st.session_state: st.session_state.ai_chat_history = []
if 'current_analysis' not in st.session_state: st.session_state.current_analysis = None

# ==========================================
# 2. AI 引擎 (支持多轮沟通)
# ==========================================
def get_ai_response(messages):
    """接入百度千帆 SDK"""
    if conf["baidu_api_key"] and conf["baidu_secret_key"]:
        try:
            chat_comp = qianfan.ChatCompletion(ak=conf["baidu_api_key"], sk=conf["baidu_secret_key"])
            resp = chat_comp.do(model="ERNIE-Bot-4", messages=messages)
            return resp.body['result']
        except Exception as e:
            return f"AI 接口调用异常: {e}"
    return "【预览模式】AI 未配置密钥。请在后台填入百度云 API Key 以激活真实建议。"

# ==========================================
# 3. HTML 报表合成器 (附件逻辑 + AI 文字)
# ==========================================
def generate_final_html(data, ai_text):
    """
    这里复刻你上传的附件 HTML 结构
    将数据（data）填入 ECharts，将 AI 文字（ai_text）填入建议区域
    """
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{conf['app_title']} - 分析报告</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f4f7f9; color: #2c3e50; }}
            .card {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .header {{ text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .ai-section {{ border-left: 5px solid #2ecc71; background: #f0fff4; padding: 15px; }}
        </style>
    </head>
    <body>
        <div class="header"><h1>教学分析周报 ({data['date']})</h1></div>
        
        <div class="card">
            <h3>📈 核心数据概览</h3>
            <p>平均出勤率: {data['attendance']*100:.1f}% | 平均正确率: {data['correctness']*100:.1f}%</p>
            <div id="mainChart" style="width:100%;height:400px;"></div>
        </div>

        <div class="card ai-section">
            <h3>🤖 AI 协作分析建议</h3>
            <div>{ai_text.replace('\\n', '<br>')}</div>
        </div>

        <script>
            var myChart = echarts.init(document.getElementById('mainChart'));
            var option = {{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: {json.dumps(data['trend_x'])} }},
                yAxis: {{ type: 'value' }},
                series: [
                    {{ name: '课时趋势', type: 'line', data: {json.dumps(data['trend_hours'])}, smooth: true, color: '#3498db' }},
                    {{ name: '正确率', type: 'line', data: {json.dumps(data['trend_cor'])}, smooth: true, color: '#e74c3c' }}
                ]
            }};
            myChart.setOption(option);
        </script>
    </body>
    </html>
    """
    return html_template

# ==========================================
# 4. 登录管理
# ==========================================
if not st.session_state.logged_in:
    st.title(conf["app_title"])
    pwd = st.text_input("请输入准入密码", type="password")
    if st.button("进入系统"):
        if pwd == conf["admin_password"]:
            st.session_state.logged_in, st.session_state.role = True, "admin"
            add_log("管理员")
            st.rerun()
        elif pwd == conf["user_password"]:
            st.session_state.logged_in, st.session_state.role = True, "user"
            add_log("普通用户")
            st.rerun()
        else:
            st.error("密码错误")
else:
    # ==========================================
    # 5. 主应用逻辑
    # ==========================================
    st.sidebar.title(f"🎭 {st.session_state.role}模式")
    nav = ["数据中心", "AI 协作区"]
    if st.session_state.role == "admin": nav.append("后台管理")
    choice = st.sidebar.radio("菜单", nav)

    if st.sidebar.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()

    if choice == "数据中心":
        st.header("📊 数据看板")
        file = st.file_uploader(conf["upload_hint"], type=["xlsx"])
        if file:
            # 此处复用你原有的 pandas 数据处理逻辑 (简化示意)
            df = pd.read_excel(file)
            df['周'] = pd.to_datetime(df['周'])
            latest = df['周'].max()
            
            # 存储分析结果
            st.session_state.current_analysis = {
                "date": latest.strftime('%Y-%m-%d'),
                "attendance": df[df['周']==latest]['课时平均出勤率'].mean(),
                "correctness": df[df['周']==latest]['题目正确率（自学+快背）'].mean(),
                "trend_x": df['周'].dt.strftime('%m-%d').unique().tolist(),
                "trend_hours": df.groupby('周')['课时数'].sum().tolist(),
                "trend_cor": (df.groupby('周')['题目正确率（自学+快背）'].mean()*100).tolist()
            }
            st.success("数据加载成功！请查看报表或进入 AI 协作区。")
            st.json(st.session_state.current_analysis)

    elif choice == "AI 协作区":
        st.header("🤖 AI 协作生成报告")
        if not st.session_state.current_analysis:
            st.warning("请先在‘数据中心’上传文件。")
        else:
            # 自动生成初始建议
            if not st.session_state.ai_chat_history:
                init_msg = f"基于最新数据：出勤率{st.session_state.current_analysis['attendance']*100:.1f}%，正确率{st.session_state.current_analysis['correctness']*100:.1f}%。请生成一份分析建议。"
                resp = get_ai_response([{"role": "user", "content": init_msg}])
                st.session_state.ai_chat_history.append({"role": "assistant", "content": resp})

            # 展示历史对话
            for m in st.session_state.ai_chat_history:
                with st.chat_message(m["role"]): st.write(m["content"])

            # 互动输入
            query = st.chat_input("您可以要求AI修改报告：例如‘字数减半’、‘语气更严厉些’...")
            if query:
                st.session_state.ai_chat_history.append({"role": "user", "content": query})
                with st.spinner("AI 正在思考..."):
                    new_resp = get_ai_response(st.session_state.ai_chat_history)
                    st.session_state.ai_chat_history.append({"role": "assistant", "content": new_resp})
                st.rerun()

            # 导出 HTML
            st.divider()
            final_ai_text = st.session_state.ai_chat_history[-1]["content"]
            final_html = generate_final_html(st.session_state.current_analysis, final_ai_text)
            st.download_button("📥 下载完整 HTML 报表 (包含 AI 建议)", final_html, "分析报告.html", "text/html")

    elif choice == "后台管理":
        st.header("⚙️ 后台设置")
        t1, t2 = st.tabs(["配置修改", "登录日志"])
        with t1:
            conf["app_title"] = st.text_input("应用名称", conf["app_title"])
            conf["user_password"] = st.text_input("普通用户密码", conf["user_password"])
            conf["baidu_api_key"] = st.text_input("百度 API Key", conf["baidu_api_key"])
            conf["baidu_secret_key"] = st.text_input("百度 Secret Key", conf["baidu_secret_key"], type="password")
            if st.button("保存更改"):
                save_config(conf); st.success("保存成功")
        with t2:
            if os.path.exists(LOG_FILE):
                st.dataframe(pd.read_csv(LOG_FILE).sort_index(ascending=False), use_container_width=True)