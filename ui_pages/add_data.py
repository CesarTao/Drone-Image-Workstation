import streamlit as st
import os


from utils.parser import parse_dji_metadata
from utils.database import save_to_db, sync_dir_tags, clear_all_data


def single_parser():
    #st.subheader("🔍 单张图片属性解析")
    uploaded_file = st.file_uploader("上传一张大疆航拍照片 (JPG)", type=['jpg', 'jpeg'])

    if uploaded_file is not None:
        # 解析
        meta = parse_dji_metadata(uploaded_file, uploaded_file.name)

        if meta:
            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(uploaded_file, caption="预览图", use_container_width=True)

            with col_info:
                st.success("✅ 解析成功！")
                st.write("### 核心参数")
                st.write(f"**📍 坐标**: {meta['GpsLatitude']}, {meta['GpsLongitude']}")
                st.write(f"**📏 绝对高度**: {meta['AbsoluteAltitude']} 米")
                st.write(f"**📷 云台俯仰**: {meta['GimbalPitchDegree']}°")

                if meta['RtkFlag'] == 50:
                    st.success("RTK状态: FIXED (固定解 - 高精度)")
                else:
                    st.warning(f"RTK状态: {meta['RtkFlag']} (非固定解)")

            with st.expander("查看所有 30+ 项原始属性", expanded=True):
                st.json(meta)
        else:
            st.error("无法提取元数据，请确认这是大疆原片。")



def multi_parser():
    #st.subheader("📂 本地文件夹批量入库")
    working_path = st.text_input("请输入NAS文件夹路径", "")
    import_type = st.radio(
        "选择要入库的文件类型：",
        ("全部", "仅图片(.jpg .jpeg)", "仅视频(.mp4 .mov)"),
        horizontal=True
    )
    if import_type == "仅图片(.jpg .jpeg)":
        target_exts = ('.jpg', '.jpeg')
    elif import_type == "仅视频(.mp4 .mov)":
        target_exts = ('.mp4', '.mov')
    else:
        target_exts = ('.jpg', '.jpeg', '.mp4', '.mov')

    if st.button("开始扫描并入库"):
        if not os.path.exists(working_path):
            st.error("路径不存在！")
        else:
            st.info(f"正在扫描: {working_path} ...")
            all_files = []
            for root, dirs, files in os.walk(working_path):
                for f in files:
                    if f.lower().endswith(target_exts):
                        all_files.append(os.path.join(root, f))

            total = len(all_files)
            st.write(f"发现 {total} 个文件。")

            progress_bar = st.progress(0)
            status_text = st.empty()

            batch_data = []
            success_count = 0

            for i, full_path in enumerate(all_files):
                # 这里的 open 逻辑需要适配
                try:
                    with open(full_path, 'rb') as f:
                        meta = parse_dji_metadata(f, os.path.basename(full_path), full_path=full_path)
                        if meta:
                            batch_data.append(meta)

                            sync_dir_tags(full_path)
                except:
                    pass

                # 批量入库
                if len(batch_data) >= 50:
                    count = save_to_db(batch_data)
                    success_count += count
                    batch_data = []

                # 更新进度
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"正在处理 ({i + 1}/{total}): {os.path.basename(full_path)}")

            # 剩余入库
            if batch_data:
                count = save_to_db(batch_data)
                success_count += count

            st.success(f"🎉 全部完成！共成功入库 {success_count} 条记录。")

    st.sidebar.markdown("---")
    st.sidebar.header("数据库管理")

    with st.sidebar.expander("🗑️ 清空数据库", expanded=False):
        st.warning("⚠️ 警告：此操作将 **永久删除** 数据库中的所有照片记录，且 **无法恢复**！")

        confirm_check = st.checkbox("确认清空", key="danger_check")

        if confirm_check:
            if st.button("🔴 立即清空所有数据", type="primary", use_container_width=True):
                with st.spinner("正在销毁数据..."):
                    if clear_all_data():
                        st.success("数据库已清空！")
                        import time

                        time.sleep(1)  # 停顿一下让用户看到成功提示
                        st.rerun()  # 刷新页面