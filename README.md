# 🚁 大疆无人机数据管理平台 (DJI Drone Data Platform)

一个基于 **Streamlit** 和 **MySQL** 构建的现代化无人机数据管理系统。专为大疆（DJI）行业无人机（如 M300, M30T, Mavic 3E 等）设计，支持海量照片元数据解析、轨迹地图可视化、目录标记管理及 AI 辅助查询。



------

## 核心功能

- **📊 数据展示与查询**：多维度筛选照片（时间、高度、云台角度、RTK状态等），支持 CSV 导出。
- **🌏 遥感采样点地图**：基于 Folium 的交互式地图，展示航拍图片的采样点位，支持矩形框选检索。
- **🔍 单张数据解析**：自动提取单张图片 EXIF/XMP 信息。
- **📂文件夹批量入库**：支持本地/NAS 文件夹递归扫描，自动去重（基于 MD5），支持jpg/jpeg/mp4/mov格式。
- **🧠 数据库实验室**：集成 DeepSeek接口，支持通过自然语言生成 SQL 进行数据查询。
- **🗃️ 目录标记管理**：为文件夹撰写备注信息、更新标签，同步更新该目录下所有文件的备注。
- **✈️ 飞行任务时长统计**：导入飞行记录 Excel，自动计算作业时长和架次。



- ![image-20260121133517416](C:\Users\Alvin\AppData\Roaming\Typora\typora-user-images\image-20260121133517416.png)

------

## 技术栈

- **前端框架**: [Streamlit](https://streamlit.io/)
- **数据库**: MySQL 8.0+
- **数据处理**: Pandas, NumPy
- **地图可视化**: Folium, Streamlit-Folium
- **元数据解析**: ExifRead (图片), Hachoir (视频)
- **AI 支持**: OpenAI SDK (兼容 DeepSeek V3)

------

## 快速开始

### 1. 环境准备

确保您的系统已安装 Python 3.8+ 和 MySQL。

```bash
# 克隆项目 (示例)
git clone https://github.com/your-repo/drone-manager.git
cd drone-manager

# 建议创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安装依赖

请根据requirements.txt运行安装命令：

```
streamlit
pandas
mysql-connector-python
exifread
folium
streamlit-folium
hachoir
openpyxl
openai
streamlit-option-menu
```

安装命令：

```bash
pip install -r requirements.txt
```

### 3. 数据库初始化

1. 登录您的 MySQL 数据库。
2. 创建一个新的数据库（例如 `dji_drone_db`）。
3. 执行项目提供的 SQL 脚本以创建数据表（sql.txt）。

### 4. 项目配置

修改 `config.py` 文件，填入您的个人信息：

```python
# config.py

DB_CONFIG = {
    'host': 'localhost',      # 数据库地址
    'user': 'root',           # 数据库用户名
    'password': 'your_password', # 数据库密码
    'database': 'dji_drone_db'   # 数据库名
}

API_KEY = "sk-..."
API_BASE = "..."
```

### 5. 启动应用

```bash
streamlit run app.py
```

启动后，浏览器将自动打开 `http://localhost:8501`。

------

## 使用指南

### 批量入库

1. 进入 **"📂 文件夹批量入库"** 页面。
2. 输入本地或挂载的 NAS 路径（如 `D:\Project\2024_Mission`）。
3. 点击开始扫描，系统会自动计算 MD5 并跳过已存在的文件。

### 地图框选

1. 进入 **"🌏 遥感采样点地图"**。
2. 使用地图左上角的 **矩形工具** 在地图上画一个框。
3. 点击左侧边栏的 **"执行筛选"**，表格将只显示框选区域内的照片。

### AI 查询 (DeepSeek)

1. 进入 **"🧠 数据库实验室"** -> 选择 **"AI 智能辅助"**。
2. 输入自然语言，例如：*"帮我找出高度大于120米且RTK状态为固定解的照片"*。
3. AI 将自动生成 SQL 并返回查询结果。





------

## ⚠️ 注意事项

- **视频解析**: 视频文件较大，解析时可能消耗较多内存，建议在服务器端运行。
- **路径格式**: 在 Windows 上输入路径时，建议使用反斜杠 `\` 或双斜杠 `\\`。
- **数据安全**: "清空数据库" 操作不可逆，请谨慎使用。



## ❓ 常见问题

**Q: 连接数据库失败 (Error 2002/1045)?**

- 检查 MySQL 服务是否已启动 (`services.msc`)。
- 检查 `secrets.toml` 或代码中的用户名密码是否正确。
- 如果是远程数据库，检查防火墙是否放行 3306 端口。

**Q: 为什么地图不显示？**

- 请确保照片中包含 GPS 信息。
- 地图加载需要互联网连接（访问高德地图瓦片服务）。如果内网环境无法上网，地图底图将无法加载。

**Q: 批量入库速度慢？**

- 入库速度取决于磁盘 I/O 和网络带宽（如果是 NAS）。
- 系统会对每张图计算 MD5 哈希以去重，大文件会增加计算时间。

