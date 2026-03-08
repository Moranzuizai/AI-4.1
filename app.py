import streamlit as st
import pandas as pd
import os
import re
import json
import datetime
import streamlit.components.v1 as components

# ==========================================
# 0. 全局配置与文件路径
# ==========================================
st.set_page_config(
    page_title="AI课堂周报生成器", 
    page_icon="📊",
    layout="wide"
)

LOG_FILE = "access_log.csv"
FEEDBACK_FILE = "feedback_log.csv"
CONFIG_FILE = "config.json"

# ==========================================
# 1. 核心工具函数
# ==========================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {"admin_password": "199266", "user_password": "a123456"}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f)
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def log_access(event_type="用户登录"):
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE):
        df_log = pd.DataFrame(columns=["访问时间", "事件"])
        df_log.to_csv(LOG_FILE, index=False)
    new_entry = pd.DataFrame([{"访问时间": now_time, "事件": event_type}])
    new_entry.to_csv(LOG_FILE, mode='a', header=False, index=False)

def save_feedback(rating, comment):
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(FEEDBACK_FILE):
        df = pd.DataFrame(columns=["时间", "评价", "建议"])
        df.to_csv(FEEDBACK_FILE, index=False)
    new_entry = pd.DataFrame([{"时间": now_time, "评价": rating, "建议": comment}])
    new_entry.to_csv(FEEDBACK_FILE, mode='a', header=False, index=False)

# ==========================================
# 2. 权限控制
# ==========================================
config = load_config()
ADMIN_PWD = config.get("admin_password", "199266")
USER_PWD = config.get("user_password", "123456")

def check_auth():
    password = st.sidebar.text_input("🔒 请输入访问密码", type="password")
    if password == ADMIN_PWD:
        return 2 
    elif password == USER_PWD:
        if 'logged_in' not in st.session_state:
            log_access("普通用户登录")
            st.session_state['logged_in'] = True
        return 1
    else:
        return 0

auth_status = check_auth()

if auth_status == 0:
    st.warning("⚠️ 请在左侧输入密码以访问系统。")
    st.stop()

# ==========================================
# 3. 管理员后台
# ==========================================
if auth_status == 2:
    st.sidebar.success("🔑 管理员已登录")
    st.title("🔧 管理员控制台")
    tab1, tab2, tab3 = st.tabs(["📝 访问日志", "💬 用户反馈", "⚙️ 系统设置"])
    with tab1:
        if os.path.exists(LOG_FILE):
            df_log = pd.read_csv(LOG_FILE).sort_values(by="访问时间", ascending=False)
            st.dataframe(df_log, use_container_width=True)
    with tab2:
        if os.path.exists(FEEDBACK_FILE):
            df_feed = pd.read_csv(FEEDBACK_FILE).sort_values(by="时间", ascending=False)
            st.dataframe(df_feed, use_container_width=True)
    with tab3:
        new_user_pwd = st.text_input("设置新的用户密码", value=USER_PWD)
        new_admin_pwd = st.text_input("设置新的管理员密码", value=ADMIN_PWD)
        if st.button("💾 保存新密码"):
            config["user_password"] = new_user_pwd
            config["admin_password"] = new_admin_pwd
            save_config(config)
            st.success("密码已更新！")
    st.stop()

# ==========================================
# 4. 普通用户界面
# ==========================================
st.title("📊 AI课堂教学数据分析工具")

def natural_sort_key(s):
    if not isinstance(s, str): s = str(s)
    trans_map = {'七': '07', '八': '08', '九': '09', '高一': '10', '高二': '11', '高三': '12'}
    s_temp = s
    for k, v in trans_map.items():
        if k in s_temp and ('级' in s_temp or '年' in s_temp):
            s_temp = s_temp.replace(k, v)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s_temp)]

def clean_percentage(x):
    if pd.isna(x) or x == '': return 0.0
    x_str = str(x).strip()
    if '%' in x_str:
        try: return float(x_str.rstrip('%')) / 100
        except: return 0.0
    else:
        try: return float(x_str)
        except: return 0.0

def get_grade(class_name):
    class_str = str(class_name)
    match = re.search(r'(.*?级)', class_str)
    if match: return match.group(1)
    return "其他"

def weighted_avg(x, col, w_col='课时数'):
    try:
        if col not in x.columns: return 0
        w_sum = x[w_col].sum()
        if w_sum == 0: return 0
        return (x[col] * x[w_col]).sum() / w_sum
    except: return 0

def get_trend_html(current, previous, is_percent=False):
    if previous is None or previous == 0: return ""
    diff = current - previous
    if abs(diff) < 0.0001: return '<span style="color:#999;font-size:14px;">(持平)</span>'
    symbol = "↑" if diff > 0 else "↓"
    color = "#2ecc71" if diff > 0 else "#e74c3c"
    diff_str = f"{abs(diff)*100:.1f}%" if is_percent else f"{int(abs(diff))}"
    return f'<span style="color:{color};font-weight:bold;">{symbol} {diff_str}</span>'

uploaded_file = st.file_uploader("请上传表格文件", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            try: df = pd.read_csv(uploaded_file, encoding='utf-8')
            except: df = pd.read_csv(uploaded_file, encoding='gbk')
        else:
            df = pd.read_excel(uploaded_file)
            
        df = df.fillna(0)
        cols_map = {}
        if '周' in df.columns: cols_map['time'] = '周'
        else: cols_map['time'] = df.columns[0]

        for c in df.columns:
            if '出勤' in c: cols_map['att'] = c
            elif '正确' in c: cols_map['corr'] = c
            elif '微课' in c and '率' in c: cols_map['micro'] = c
            elif c == '课时数': cols_map['hours'] = c 
            elif '环节完成率' in c: cols_map['comp'] = c
            elif '班级' in c: cols_map['class'] = c
            elif '学科' in c: cols_map['subject'] = c
        
        for k in ['att', 'corr', 'micro', 'comp']:
            if k in cols_map and cols_map[k] in df.columns:
                df[cols_map[k]] = df[cols_map[k]].apply(clean_percentage)
        
        time_col = cols_map['time']
        df = df[df[time_col].astype(str) != '合计']
        all_periods = sorted([str(x) for x in df[time_col].unique()], key=natural_sort_key)
        
        target_week = all_periods[-1]
        prev_week = all_periods[-2] if len(all_periods) > 1 else None
        
        df_curr = df[df[time_col].astype(str) == target_week].copy()
        df_prev = df[df[time_col].astype(str) == prev_week].copy() if prev_week else None
        df_curr['年级'] = df_curr[cols_map['class']].apply(get_grade)
        
        def calc_metrics(d):
            if d is None or d.empty: return None
            return {
                'hours': int(d[cols_map['hours']].sum()),
                'att': weighted_avg(d, cols_map['att'], cols_map['hours']),
                'corr': weighted_avg(d, cols_map['corr'], cols_map['hours'])
            }
        m_curr = calc_metrics(df_curr)
        m_prev = calc_metrics(df_prev)
        
        t_h = get_trend_html(m_curr['hours'], m_prev['hours'], False) if m_prev else ""
        t_a = get_trend_html(m_curr['att'], m_prev['att'], True) if m_prev else ""
        t_c = get_trend_html(m_curr['corr'], m_prev['corr'], True) if m_prev else ""
            
        class_stats = df_curr.groupby(['年级', cols_map['class']]).apply(
            lambda x: pd.Series({
                '课时数': int(x[cols_map['hours']].sum()),
                '出勤率': weighted_avg(x, cols_map['att'], cols_map['hours']),
                '微课完成率': weighted_avg(x, cols_map['micro'], cols_map['hours']) if 'micro' in cols_map else 0,
                '题目正确率': weighted_avg(x, cols_map['corr'], cols_map['hours']),
                '主要学科': ','.join(x[cols_map['subject']].astype(str).unique()) if 'subject' in cols_map else '-'
            })
        ).reset_index()
        chart_df = class_stats.sort_values(by=cols_map['class'], key=lambda x: x.map(natural_sort_key))
        
        c_cats = json.dumps(chart_df[cols_map['class']].tolist(), ensure_ascii=False)
        c_hours = json.dumps(chart_df['课时数'].tolist())
        c_att = json.dumps([round(x*100, 1) for x in chart_df['出勤率'].tolist()])
        c_corr = json.dumps([round(x*100, 1) for x in chart_df['题目正确率'].tolist()])
        
        all_class_stats = df.groupby(cols_map['class']).apply(
            lambda x: pd.Series({
                '课时数': int(x[cols_map['hours']].sum()),
                '完成率': weighted_avg(x, cols_map['comp'], cols_map['hours']),
                '正确率': weighted_avg(x, cols_map['corr'], cols_map['hours'])
            })
        ).reset_index().sort_values(by=cols_map['class'], key=lambda x: x.map(natural_sort_key))
        
        a_cats = json.dumps(all_class_stats[cols_map['class']].tolist(), ensure_ascii=False)
        a_hours = json.dumps(all_class_stats['课时数'].tolist())
        a_comp = json.dumps([round(x*100, 1) for x in all_class_stats['完成率'].tolist()])
        a_corr = json.dumps([round(x*100, 1) for x in all_class_stats['正确率'].tolist()])

        tables_html = ""
        for grade in sorted(class_stats['年级'].unique(), key=natural_sort_key):
            g_df = class_stats[class_stats['年级'] == grade].sort_values(by='课时数', ascending=False)
            tables_html += f"<h3>{grade}</h3><table><thead><tr><th>班级</th><th>学科</th><th>课时</th><th>出勤</th><th>正确率</th></tr></thead><tbody>"
            for _, row in g_df.iterrows():
                tables_html += f"<tr><td>{row[cols_map['class']]}</td><td>{row['主要学科']}</td><td>{int(row['课时数'])}</td><td>{row['出勤率']*100:.1f}%</td><td>{row['题目正确率']*100:.1f}%</td></tr>"
            tables_html += "</tbody></table>"

        hist_stats = df.groupby(time_col).apply(
            lambda x: pd.Series({
                '课时数': int(x[cols_map['hours']].sum()),
                '出勤率': weighted_avg(x, cols_map['att'], cols_map['hours']),
                '题目正确率': weighted_avg(x, cols_map['corr'], cols_map['hours'])
            })
        ).reset_index().sort_values(by=time_col, key=lambda x: x.map(natural_sort_key))
        
        t_dates = json.dumps(hist_stats[time_col].tolist(), ensure_ascii=False)
        t_hours = json.dumps(hist_stats['课时数'].tolist())
        t_att = json.dumps([round(x*100, 1) for x in hist_stats['出勤率'].tolist()])
        t_corr = json.dumps([round(x*100, 1) for x in hist_stats['题目正确率'].tolist()])

        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <style>
            body {{ font-family: sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f4f6f9; }}
            .card {{ background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; }}
            .kpi {{ display: flex; justify-content: space-around; text-align: center; }}
            .kpi strong {{ font-size: 24px; color: #2980b9; display: block; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: center; }}
            .chart {{ height: 400px; width: 100%; }}
        </style></head>
        <body>
            <h2 style="text-align:center">AI课堂数据周报 ({target_week})</h2>
            <div class="card"><div class="kpi">
                <div><strong>{m_curr['hours']}{t_h}</strong>总课时</div>
                <div><strong>{m_curr['att']*100:.1f}%{t_a}</strong>出勤率</div>
                <div><strong>{m_curr['corr']*100:.1f}%{t_c}</strong>正确率</div>
            </div></div>
            <div class="card"><h3>🏫 班级效能 (本周)</h3><div id="c1" class="chart"></div></div>
            <div class="card"><h3>📋 数据明细</h3>{tables_html}</div>
            <div class="card"><h3>🏛️ 全周期班级累计</h3><div id="c3" class="chart"></div></div>
            <div class="card"><h3>📈 历史趋势</h3><div id="c2" class="chart"></div></div>
            <script>
                var opt = (title, cats, d1, d2, d3, n1, n2, n3) => ({{
                    tooltip: {{trigger:'axis'}}, legend: {{bottom:0}},
                    xAxis: {{type:'category', data:cats, axisLabel:{{rotate:35}}}},
                    yAxis: [{{type:'value', name:n1}}, {{type:'value', name:'%', max:100}}],
                    series: [
                        {{type:'bar', name:n1, data:d1}},
                        {{type:'line', yAxisIndex:1, name:n2, data:d2}},
                        {{type:'line', yAxisIndex:1, name:n3, data:d3}}
                    ]
                }});
                echarts.init(document.getElementById('c1')).setOption(opt('本周', {c_cats}, {c_hours}, {c_att}, {c_corr}, '课时', '出勤', '正确'));
                echarts.init(document.getElementById('c3')).setOption(opt('全周期', {a_cats}, {a_hours}, {a_comp}, {a_corr}, '累计课时', '完成率', '正确率'));
                echarts.init(document.getElementById('c2')).setOption(opt('趋势', {t_dates}, {t_hours}, {t_att}, {t_corr}, '课时', '出勤', '正确'));
            </script>
        </body></html>
        """
        st.download_button("📥 下载报表", html_content, f"分析报表.html", "text/html")
        components.html(html_content, height=1000, scrolling=True)
        
    except Exception as e:
        st.error(f"发生错误：{str(e)}")
