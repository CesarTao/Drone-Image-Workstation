import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, MarkerCluster

from utils.database import load_data_from_db


def render_map():
    
    #st.subheader("🗺️ 采样点位分布")

    if 'params_snapshot' not in st.session_state:
        st.session_state['params_snapshot'] = {
            'drawings':[],
            'is_submitted': False
        }

    if 'shared_map_data' in st.session_state and not st.session_state['shared_map_data'].empty:
        # 优先使用传过来的筛选数据
        df = st.session_state['shared_map_data']
        data_source_text = "🔍 来自【数据查询】的筛选结果"
        is_filtered_view = True
    else:
        # 如果没有，则加载全量数据库
        try:
            df = load_data_from_db()
            data_source_text = "💾 全量数据库"
            is_filtered_view = False
        except:
            st.stop()

    with st.sidebar.form(key='filter_form'):
        st.sidebar.markdown("---")
        st.sidebar.header("地图控制")

        # 1. 简单的侧边栏筛选 (为了方便看图，只留最核心的)
        # show_rtk_only = st.sidebar.checkbox("只显示 RTK 固定解", value=False)
        # map_style = st.sidebar.selectbox("地图风格", ["卫星/深色 (Satellite)", "街道/浅色 (Road)"])
        point_radius = st.sidebar.slider("轨迹点大小", 1, 20, 5)

        # 2. 数据处理
        map_df = df.copy()
        # if show_rtk_only:
        #    map_df = map_df[map_df['RtkFlag'] == 50]

        # 必须清除无效坐标
        map_df = map_df.dropna(subset=['GpsLatitude', 'GpsLongitude'])
        map_df = map_df[(map_df['GpsLatitude'] != 0) & (map_df['GpsLongitude'] != 0)]

        max_points = st.sidebar.slider("展示数据点个数", 1, len(map_df), 2000)

        submit_btn = st.form_submit_button(label='执行筛选',type="primary")

    # max_points = 10000
    if len(map_df) > max_points:
        st.warning(f"数据量较大，仅显示前{max_points}个数据点")
        map_df = map_df.head(max_points)

    if map_df.empty:
        st.warning("当前没有包含 GPS 坐标的照片数据。")
    else:
        # 3. 动态计算地图中心和缩放
        # 取平均值作为中心
        mid_lat = map_df['GpsLatitude'].mean()
        mid_lon = map_df['GpsLongitude'].mean()
        if len(map_df) >= 50:
            zoom_start = 10
        elif len(map_df) >= 20:
            zoom_start = 12
        else:
            zoom_start = 16

        m = folium.Map(
            location=[mid_lat, mid_lon],
            zoom_start=zoom_start,
            control_scale=True,
            # 使用高德地图底图 (需要网络能访问高德)
            tiles='https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}',
            #tiles='CartoDB positron',
            attr='高德地图'
        )

        # 往地图上加点
        #for index, row in map_df.iterrows():
        #    popup_info = f"{row['filename']}<br>{row['capture_time']}"
        #    folium.CircleMarker(
        #        location=[row['GpsLatitude'], row['GpsLongitude']],
        #        popup=popup_info,
        #        radius=point_radius,
        #        color='red',
        #        fill=True,
        #        fill_color='red',
        #        tooltip=f"{row['filename']} (高度: {row['AbsoluteAltitude']}m)"
        #    ).add_to(m)

        marker_cluster = MarkerCluster(name="聚合图层", disable_clustering_at_zoom=16).add_to(m)

        points_data = map_df[['GpsLatitude', 'GpsLongitude', 'filename', 'AbsoluteAltitude']].values

        # 循环添加点到聚合器
        markers = []
        for lat, lon, fname, alt in points_data:
            popup_txt = f"<b>{fname}</b><br>高度: {alt}m"
            
            marker = folium.CircleMarker(
                location=[lat, lon],
                radius=5,           # 聚合展开后的点大小
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=0.7,
                tooltip=fname,      # 鼠标悬停显示文件名
                popup=popup_txt
            )
            markers.append(marker)


        for marker in markers:
            marker.add_to(marker_cluster)


        # 渲染地图
        # st_folium(m, width=None, height=620)

        st.sidebar.info(f"当前地图展示了 {len(map_df)} 个轨迹点。")

        draw = Draw(
            export=False,
            position='topleft',
            draw_options={
                'polyline': False,
                'polygon': False,
                'circle': False,
                'marker': False,
                'circlemarker': False,
                'rectangle': True  # 只开启矩形框选
            }
        )
        draw.add_to(m)

        # st.markdown("### 🗺️ 地图框选检索")
        # st.info("💡 使用地图左上角的矩形工具框选区域，下方将自动显示选中范围内的文件。")

        # 4. 渲染地图并获取输出
        # width 设为 100% 可能会有显示 bug，建议设为固定值或 null
        output = st_folium(m, width=None, height=600)

        #
        
        if submit_btn:
            current_drawings = []
            if output and 'all_drawings' in output:
                current_drawings = output['all_drawings']
            st.session_state['params_snapshot'] = {
                'drawings': current_drawings,
                'is_submitted': True
            }
            st.rerun()
        

        snapshot = st.session_state['params_snapshot']

        if snapshot['is_submitted']:
            st.divider()
            st.subheader("📊 筛选结果")
            
            with st.spinner("正在计算 20,000+ 条数据的位置关系..."):
                filtered_df = map_df.copy()

                drawings = snapshot['drawings']
                if drawings:
                    final_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                    box_count = 0
                    
                    for shape in drawings:
                        if shape['geometry']['type'] == 'Polygon':
                            coords = shape['geometry']['coordinates'][0]
                            lons = [p[0] for p in coords]
                            lats = [p[1] for p in coords]
                            
                            mask = (
                                (filtered_df['GpsLatitude'] >= min(lats)) & 
                                (filtered_df['GpsLatitude'] <= max(lats)) & 
                                (filtered_df['GpsLongitude'] >= min(lons)) & 
                                (filtered_df['GpsLongitude'] <= max(lons))
                            )
                            final_mask = final_mask | mask
                            box_count += 1
                        else:
                            st.info("地图上未绘制选区，显示符合其他条件的数据。")

                    filtered_df = filtered_df[final_mask]
                    st.success(f"共找到 {len(filtered_df)} 条数据")
                    st.dataframe(filtered_df, use_container_width=True)
                
                else:
                    st.info("👈 请在左侧设置条件，并在地图上画框后，点击【执行筛选】按钮查看结果。")
