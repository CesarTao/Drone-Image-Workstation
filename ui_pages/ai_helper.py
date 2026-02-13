import streamlit as st
from datetime import datetime


from utils.database import execute_raw_sql
from utils.llm import generate_sql_from_ai
from config import API_BASE, API_KEY


def ai_helper():

    st.sidebar.markdown("---")
    st.sidebar.header("模式选择")
    sub_mode = st.sidebar.radio("✨ AI模式", ["🛠️ SQL手动查询", "🤖 AI智能辅助"])

    if sub_mode == "🛠️ SQL手动查询":
        #st.markdown("### 👨‍💻 SQL控制台")
        result_container = st.container()
        st.caption("在此处输入标准的 MySQL 查询语句。")

        # 布局：左边是输入框，右边是表结构参考 (防忘词)
        col_edit, col_schema = st.columns([3, 1])

        with col_schema:
            st.info("📚 属性名称参考")
            st.code("""
id, filename, Version
FilePath, FolderName
capture_time, created_time
GpsLatitude, GpsLongitude
AbsoluteAltitude, RelativeAltitude
FlightXSpeed, FlightYSpeed
DroneModel
FileHash
                """, language="text")

        with col_edit:
            # 默认给一个示例 SQL
            default_sql = """-- 示例：查询最近上传的 10 张照片
SELECT id, filename, capture_time, FolderName, AbsoluteAltitude 
FROM drone_photos 
ORDER BY capture_time DESC 
LIMIT 10;"""

            # SQL 输入区域 (高度调高一点)
            txt_sql = st.text_area("输入 SQL 脚本:", value=default_sql, height=250)

            # 执行按钮
            run_col1, run_col2 = st.columns([1, 4])
            with run_col1:
                btn_run = st.button("▶️ 执行查询", type="primary", use_container_width=True)
            with run_col2:
                st.caption("")

        # 2. 结果展示区域
        st.divider()
        if btn_run:
            if not txt_sql.strip():
                st.warning("请输入 SQL 语句。")
            else:
                with st.spinner("正在查询数据库..."):
                    df_res, error_msg = execute_raw_sql(txt_sql)

                    if error_msg:
                        st.error(f"❌ 执行失败: \n{error_msg}")
                    elif df_res is not None:
                        # 成功获取数据
                        with result_container:
                            st.success(f"✅ 查询成功！返回 {len(df_res)} 行记录。")
                            st.dataframe(df_res, use_container_width=True)
                            st.download_button(
                                label="📥 下载查询结果 (CSV)",
                                data=df_res.to_csv(index=False).encode('utf-8-sig'),
                                file_name=f"sql_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime='text/csv'
                            )

                    else:
                        st.info("查询执行成功，但没有返回数据（结果集为空）。")


    elif sub_mode == "🤖 AI智能辅助":
        st.markdown("### 🤖 AI 数据分析助手")
        st.caption(
            "基于 DeepSeek V3/R1 模型。用自然语言提问，AI 自动生成 SQL 并执行。如果没有指定数量，默认显示20条数据。")
        api_key_input = API_KEY
        api_base = API_BASE

        chat_container = st.container()
        user_text = st.chat_input("请输入你的问题 (例如: 帮我找出高度大于100米的照片)")
        if user_text:
            with chat_container:
                st.chat_message("user").write(user_text)

                if not api_key_input:
                    st.chat_message("assistant").error("❌ API Key 未配置")
                else:
                    with st.spinner("🤖 AI 正在思考中..."):
                        generated_sql, err = generate_sql_from_ai(user_text, api_key_input, api_base)
                    if err:
                        st.chat_message("assistant").error(err)
                    else:
                        # 显示生成的 SQL (让用户确认，增加透明度)
                        msg = st.chat_message("assistant")
                        msg.caption("生成 SQL:")
                        msg.code(generated_sql, language="sql")

                        # C. 自动执行 SQL
                        df_result, db_err = execute_raw_sql(generated_sql)

                        if db_err:
                            msg.error(f"⚠️ SQL 执行报错: {db_err}")
                            msg.warning("可能是 AI 生成的字段名不对，请尝试换个问法。")
                        elif df_result is not None:
                            if df_result.empty:
                                st.info("查询执行成功，但没有找到符合条件的数据。")
                            else:
                                msg.success(f"✅ 查询成功，共 {len(df_result)} 条结果：")
                                msg.dataframe(df_result, use_container_width=True)
