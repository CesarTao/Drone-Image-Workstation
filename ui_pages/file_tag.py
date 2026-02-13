import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
import time

from config import DB_CONFIG
from utils.database import update_color_by_hashes, update_marks_batch
from utils.common import color_wash, standardize_color

TAG_OPTIONS = [
        "⚪",
        "🔴",
        "🟡",
        "🟢",
        "🔵"
]

def file_tag():
    #st.subheader("🗂️ 目录层级标记管理")
    
    conn = mysql.connector.connect(**DB_CONFIG)
    sql = """
    SELECT
        folder_name, 
        full_path,
        t.dir_level_1 AS '一级目录',
        t.dir_level_2 AS '二级目录',
        t.dir_level_3 AS '三级目录',
        t.tag_color,
        t.mark_note
    FROM file_dir_tags t
    ORDER BY t.updated_at DESC
    LIMIT 2000;
    """
    df_tags = pd.read_sql(sql, conn)
    conn.close()

    if df_tags.empty:
        st.warning("暂无数据。")
        st.stop()

    df_tags['tag_color'] = df_tags['tag_color'].fillna("⚪")
    df_tags['mark_note'] = df_tags['mark_note'].fillna("")

    c1, c2, c3, c4, c5= st.columns([1, 1, 1, 1, 1])
    
    with c1:
        # 默认不选任何东西表示“全选”
        selected_colors = st.multiselect(
            "🎨 按颜色标签筛选", 
            options=TAG_OPTIONS[1:], # 排除掉“无”
            default=[]
        )
    with c2:
        # 获取去重后的列表
        all_l2_dirs = list(df_tags['一级目录'].dropna().unique())
        all_l2_dirs.sort()
        filter_l2_dirs = st.multiselect("📂 按一级目录筛选", all_l2_dirs)

    with c3:
        all_l3_dirs = list(df_tags['二级目录'].dropna().unique())
        all_l3_dirs.sort()
        filter_l3_dirs = st.multiselect("🗂️ 按二级目录筛选", all_l3_dirs)
    
    with c4:
        all_l4_dirs = list(df_tags['三级目录'].dropna().unique())
        all_l4_dirs.sort()
        filter_l4_dirs = st.multiselect("🗂️ 按三级目录筛选", all_l4_dirs)

    # 关键字搜索
    with c5:
        search_txt = st.text_input("🔍 搜索文件名/备注", "")

    df_display = df_tags.copy()

    if selected_colors:
        df_display = df_display[df_display['tag_color'].isin(selected_colors)]

    if filter_l2_dirs:
        df_display = df_display[df_display['一级目录'].isin(filter_l2_dirs)]
    if filter_l3_dirs:
        df_display = df_display[df_display['二级目录'].isin(filter_l3_dirs)]
    if filter_l4_dirs:
        df_display = df_display[df_display['三级目录'].isin(filter_l4_dirs)]

    if search_txt:
        df_display = df_display[
            df_display['filename'].str.contains(search_txt, case=False, na=False) | 
            df_display['mark_note'].str.contains(search_txt, case=False, na=False)
        ]
        
    #if selected_colors:
    #    df_display = df_tags[df_tags['tag_color'].isin(selected_colors)].copy()
    #else:
    #    df_display = df_tags.copy()
        
    

    # 3. 交互编辑表格 (Selectbox)
    #st.markdown("### 📝 状态管理")
    

    if not df_display.empty:
        col_batch_1, col_batch_2, col_batch_3, col_batch_4, col_kpi = st.columns([2, 0.7, 0.95, 1, 2])
        col_batch_5, = st.columns([3])
        st.markdown("---")

        #with col_batch_1:
            #st.subheader("状态管理")
            #target_color = st.selectbox(
            #    "将所有筛选结果统一标记为:", 
            #    TAG_OPTIONS, 
            #    index=0,
            #    key="batch_target_color"
            #)
        with col_batch_4:
            df_export = df_display[[
                'full_path', 'folder_name', 'mark_note', 'tag_color', 
                '一级目录', '二级目录', '三级目录'
            ]].copy()
            df_export['tag_color'] = df_export['tag_color'].apply(color_wash)
        
            # 导出 CSV (UTF-8-SIG 避免中文乱码)
            csv_data = df_export.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="下载 CSV 表格",
                data=csv_data,
                file_name=f"导出_{datetime.now().strftime('%Y%m%d')}.csv",
                use_container_width=True
            )
            # st.info("💡 提示：修改时请勿改动 'full_path' 列，它是系统的唯一索引。")


        with col_batch_5:
            uploaded_tag_file = st.file_uploader("上传数据表格", type=['csv', 'xlsx'])
            if uploaded_tag_file:
                try:
                    if uploaded_tag_file.name.endswith('.csv'):
                        df_upload = pd.read_csv(uploaded_tag_file)
                    else:
                        df_upload = pd.read_excel(uploaded_tag_file)
                    
                    st.success(f"读取成功！共 {len(df_upload)} 行数据。")
                    
                    col_map = {
                        "完整路径": "full_path",
                        "备注": "mark_note",
                        "备注信息": "mark_note",
                        "标记": "tag_color",
                        "颜色": "tag_color"
                    }
                    df_upload = df_upload.rename(columns=col_map)

                    # 关键字段检查
                    if 'full_path' not in df_upload.columns:
                        st.error("❌ 错误：文件中缺少 'full_path' (完整路径) 列，无法定位数据。")
                    else:
                        df_upload['tag_color'] = df_upload['tag_color'].apply(standardize_color)
                        # 预览差异
                        st.dataframe(df_upload.head())

                        # 执行更新
                        if st.button("🚀 确认覆盖并同步数据库"):
                            with st.spinner("正在批量解析并同步..."):
                                update_marks_batch(df_upload, 2)
                                st.success("导入完成！页面即将刷新...")
                                time.sleep(1.5)
                                st.rerun()
                                
                except Exception as e:
                    st.error(f"文件解析失败: {e}")

        with col_batch_2:
            btn = st.button("保存修改")
        #with col_batch_3:
            #select_btn = st.button("全部更新", False)
            #if select_btn:
            #    target_hashes = df_display['file_hash'].tolist()
            #    select_btn = False
            #    
            #    with st.spinner("正在批量更新数据库..."):
            #        update_color_by_hashes(target_hashes, target_color)
            #        st.rerun() # 刷新看结果

        with col_batch_3:
            save_btn = st.button("同步至数据库")   

        # KPI 展示
        with col_kpi:
            count = len(df_display)
            st.metric("当前显示", f"{count} 个文件")    


    else:
        st.caption("没有符合筛选条件的文件，无法执行批量操作。")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            # 使用下拉框列
            "tag_color": st.column_config.SelectboxColumn(
                "标记",
                help="点击选择文件的状态颜色",
                width="small",
                options=TAG_OPTIONS,
                required=True
            ),
            "mark_note": st.column_config.TextColumn(
                "📝 备注信息",
                help="备注将会同步到文件夹下的所有文件下",
                width="large"
            ),
            # 锁定其他列
            "full_path": None,
            "filename": None,
            "一级目录": st.column_config.TextColumn(disabled=True),
            "二级目录": st.column_config.TextColumn(disabled=True),
            "三级目录": st.column_config.TextColumn(disabled=True),
        },
        disabled=["full_path", "filename", "根目录", "子目录", "任务目录"],
        hide_index=True,
        use_container_width=True,
        height=600,
        key="color_tag_editor"
    )

    # 4. 保存按钮
    if btn:
        with st.spinner("正在保存修改..."):
            update_marks_batch(edited_df, 1)
            st.rerun()
    if save_btn:
        with st.spinner("正在更新数据库..."):
            update_marks_batch(edited_df, 2)
            #target_hashes = df_display['file_hash'].tolist()
            #select_btn = False
            
            #update_color_by_hashes(target_hashes, target_color)
            st.rerun() # 刷新看结果