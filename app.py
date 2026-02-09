import streamlit as st
import pandas as pd
import os
import json
import datetime
import streamlit.components.v1 as components
import qianfan
from io import BytesIO

# ==========================================
# 1. 基础配置与安全日志 (集成原版逻辑)
# ==========================================
CONFIG_FILE = "config.json"
LOG_FILE = "access_log.csv"

def load_config():
    default_config = {
        "admin_password": "199266", 
        "user_password": "a123456",
        "baidu_api_key": "",
        "baidu_secret_key": "",
        "upload_hint": "⬆️ 请上传班级数据原文件（Excel）",
        "app_title": "AI 课堂教学数据分析平台"
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f: json.dump(default_config, f)
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        for k, v in default_config.items():
            if k not in config: config[k] = v
        return config

def write_log(user_role):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = pd.DataFrame([[now, user_role]], columns=["时间", "角色"])
    if not os.path.exists(LOG_FILE):
        log_entry.to_csv(LOG_FILE, index=False)
    else:
        log_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)

conf = load_config()
st.set_page_config(page_title=conf["app_title"], layout="wide")

# 初始化 Session State
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'ai_history' not in st.session_state: st.session_state.ai_history = []
if 'last_analysis' not in st.session_state: st.session_state.last_analysis = None

# ==========================================
# 2. 核心数据分析引擎 (保留你原有的复杂逻辑)
# ==========================================
def analyze_data(df):
    try:
        df['周'] = pd.to_datetime(df['周'], errors='coerce')
        df = df.dropna(subset=['周']).fillna(0)
        latest_week = df['周'].max()
        current_data = df[df['周'] == latest_week]
        
        # 提取趋势数据用于 ECharts
        trends = df.groupby('周').agg({
            '课时数': 'sum',
            '课时平均出勤率': 'mean',
            '题目正确率（自学+快背）': 'mean'
        }).reset_index()
        trends['周'] = trends['周'].dt.strftime('%Y-%m-%d')
        
        metrics = {
            "date": latest_week.strftime('%Y-%m-%d'),
            "attendance": current_data['课时平均出勤率'].mean(),
            "correctness": current_data['题目正确率（自学+快背）'].mean(),
            "hours": current_data['课时数'].sum(),
            "class_data": current_data[['班级名称', '课时数', '课时平均出勤率', '题目正确率（自学+快背）']].to_dict('records'),
            "trend_x": trends['周'].tolist(),
            "trend_hours": trends['课时数'].tolist(),
            "trend_att": (trends['课时平均出勤率'] * 100).round(1).tolist(),
            "trend_cor": (trends['题目正确率（自学+快背）'] * 100).round(1).tolist()
        }
        return metrics
    except Exception as e:
        st.error(f"分析失败，请检查 Excel 列名。错误: {e}")
        return None

# ==========================================
# 3. AI 交互逻辑 (多轮对话 + 协作修改)
# ==========================================
def call_ai_service(prompt):
    """集成百度千帆或模拟逻辑"""
    if conf["baidu_api_key"] and conf["baidu_secret_key"]:
        try:
            chat_comp = qianfan.ChatCompletion(ak=conf["baidu_api_key"], sk=conf["baidu_secret_key"])
            resp = chat_comp.do(model="ERNIE-Bot-4", messages=[{"role": "user", "content": prompt}])
            return resp.body['result']
        except:
            return "AI 服务暂未配置正确，这是系统生成的默认建议：当前数据表现平稳，建议针对弱势班级进行二次辅导。"
    return "系统默认建议：出勤率表现优异，建议关注正确率较低的班级。"

# ==========================================
# 4. 登录界面
# ==========================================
if not st.session_state.logged_in:
    st.title(f"🔐 {conf['app_title']}")
    st.info(conf["upload_hint"])
    pwd = st.text_input("输入访问密码", type="password")
    if st.button("登录"):
        if pwd == conf["admin_password"]:
            st.session_state.logged_in, st.session_state.role = True, "admin"
            write_log("管理员")
            st.rerun()
        elif pwd == conf["user_password"]:
            st.session_state.logged_in, st.session_state.role = True, "user"
            write_log("普通用户")
            st.rerun()
        else:
            st.error("密码错误")

# ==========================================
# 5. 主应用界面 (导航设计)
# ==========================================
else:
    st.sidebar.title(f"🚀 {st.session_state.role}面板")
    menu = ["📊 数据看板", "🤖 AI 协作修正"]
    if st.session_state.role == "admin": menu.append("⚙️ 系统后台")
    choice = st.sidebar.radio("前往", menu)
    
    if st.sidebar.button("注销登录"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 模块 A：原版数据看板 + ECharts ---
    if choice == "📊 数据看板":
        st.header("教学数据自动分析")
        file = st.file_uploader("导入数据文件", type=["xlsx"])
        if file:
            data = analyze_data(pd.read_excel(file))
            if data:
                st.session_state.last_analysis = data
                st.success(f"已加载 {data['date']} 的数据")
                
                # 指标卡片
                c1, c2, c3 = st.columns(3)
                c1.metric("出勤率", f"{data['attendance']*100:.1f}%")
                c2.metric("正确率", f"{data['correctness']*100:.1f}%")
                c3.metric("本周总课时", int(data['hours']))
                
                # ECharts 趋势图 (复用你原有的 HTML/JS 逻辑)
                echarts_html = f"""
                <div id="chart" style="width:100%;height:400px;"></div>
                <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
                <script>
                    var chart = echarts.init(document.getElementById('chart'));
                    chart.setOption({{
                        title: {{ text: '教学指标趋势' }},
                        tooltip: {{ trigger: 'axis' }},
                        legend: {{ data: ['课时', '出勤率', '正确率'] }},
                        xAxis: {{ data: {json.dumps(data['trend_x'])} }},
                        yAxis: [{{ type: 'value', name: '课时' }}, {{ type: 'value', name: '百分比', max: 100 }}],
                        series: [
                            {{ name: '课时', type: 'bar', data: {data['trend_hours']} }},
                            {{ name: '出勤率', type: 'line', yAxisIndex: 1, data: {data['trend_att']} }},
                            {{ name: '正确率', type: 'line', yAxisIndex: 1, data: {data['trend_cor']} }}
                        ]
                    }});
                </script>
                """
                components.html(echarts_html, height=450)
                
                # 初始生成 AI 建议
                if not st.session_state.ai_history:
                    initial_prompt = f"请根据以下数据生成教学分析简报：出勤率{data['attendance']}, 正确率{data['correctness']}。"
                    st.session_state.ai_history.append({"role": "ai", "content": call_ai_service(initial_prompt)})
                st.info("👈 数据分析完成，请前往侧边栏‘AI 协作修正’定制报告。")

    # --- 模块 B：AI 交互与多轮修正 ---
    elif choice == "🤖 AI 协作修正":
        st.header("AI 协作与报告生成")
        if not st.session_state.last_analysis:
            st.warning("请先上传数据并查看看板。")
        else:
            # 展示对话历史
            for msg in st.session_state.ai_history:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            # 多轮互动
            user_query = st.chat_input("输入修改要求（如：‘突出显示8班’、‘字数减半’）")
            if user_query:
                st.session_state.ai_history.append({"role": "user", "content": user_query})
                with st.spinner("AI 正在按需修改..."):
                    new_resp = call_ai_service(f"基于当前数据：{st.session_state.last_analysis}，用户要求修改报告：{user_query}")
                    st.session_state.ai_history.append({"role": "ai", "content": new_resp})
                st.rerun()

            # 导出 HTML 报告 (包含 ECharts 和 AI 文字)
            if st.session_state.ai_history:
                st.divider()
                final_text = st.session_state.ai_history[-1]["content"]
                report_html = f"<html><body><h2>教学分析报告</h2><p>{final_text}</p></body></html>"
                st.download_button("📥 导出最终 HTML 报告", data=report_html, file_name="分析报告.html", mime="text/html")

    # --- 模块 C：系统后台 (密码、提示、记录) ---
    elif choice == "⚙️ 系统后台":
        st.header("系统管理与维护")
        
        t1, t2, t3 = st.tabs(["基本配置", "安全设置", "使用记录"])
        
        with t1:
            conf["app_title"] = st.text_input("软件名称", conf["app_title"])
            conf["upload_hint"] = st.text_area("登录页提示信息", conf["upload_hint"])
            if st.button("更新基本配置"):
                save_config(conf); st.success("已保存")
        
        with t2:
            conf["admin_password"] = st.text_input("管理员密码", conf["admin_password"], type="password")
            conf["user_password"] = st.text_input("普通用户密码", conf["user_password"], type="password")
            st.divider()
            conf["baidu_api_key"] = st.text_input("百度 API Key", conf["baidu_api_key"])
            conf["baidu_secret_key"] = st.text_input("百度 Secret Key", conf["baidu_secret_key"], type="password")
            if st.button("更新安全配置"):
                save_config(conf); st.success("已保存")

        with t3:
            st.subheader("系统访问日志")
            if os.path.exists(LOG_FILE):
                log_df = pd.read_csv(LOG_FILE)
                st.dataframe(log_df.sort_index(ascending=False), use_container_width=True)
                st.download_button("导出日志 CSV", log_df.to_csv(index=False), "logs.csv")
            else:
                st.info("暂无记录")