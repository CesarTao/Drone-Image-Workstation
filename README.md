# 大疆无人机遥感照片解析工具

基于 Streamlit 开发的综合性航测数据管理平台。可使用范围包括大疆 (DJI) 行业无人机（如 M300, M30T, Mavic 3E）设计，支持照片元数据自动提取、轨迹地图可视化、SQL 数据查询及 AI 智能辅助功能。

![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg) ![Python](https://img.shields.io/badge/Python-3.9+-3776AB.svg) ![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1.svg)



## ✨ 主要功能

1.  **📊 数据展示与查询**: 支持按时间、机型、高度、RTK 状态等多维度筛选，实时统计照片数量与存储占用。
2.  **🌏 遥感采样点地图**: 自动提取照片 GPS 坐标，在交互式地图上绘制飞行轨迹点，支持查看每个点的高度与文件名。
3.  **📂 文件夹批量入库**: 
    - 支持单张图片解析预览。
    - 支持本地/NAS 文件夹批量扫描入库。
    - **去重机制**: 基于 MD5 哈希校验，防止重复入库。
4.  **🚁 元数据深度解析**: 提取 30+ 项参数，包括：
    - 绝对/相对高度、云台角度 (Pitch/Yaw/Roll)、机身姿态。
    - RTK 状态及精度误差 (StdLon/StdLat/StdHgt)。
    - 激光测距数据 (针对 M30T 等机型)。
5.  **🧠 数据库实验室**:
    - **SQL 控制台**: 支持手动执行 SQL 查询并导出 CSV。
    - **🤖 AI 智能问数辅助: 接入 DeepSeek 大模型，支持自然语言转 SQL (Text-to-SQL)，例如：“找出高度大于100米且RTK为固定解的照片”。



------

## 🛠️ 部署指南

### 1. 环境准备
确保你的电脑已安装：
* Python 3.9 或更高版本
* MySQL 8.0 或更高版本
* Git (可选)

### 2. 安装依赖
下载代码后，在项目根目录运行以下命令安装 Python 库：

```bash
pip install streamlit pandas mysql-connector-python exifread pydeck folium streamlit-folium openai protobuf
```

### 3. 数据库构建

请在 MySQL 数据库管理工具（如 SQLyog, Navicat, DBeaver）中执行以下 SQL 脚本，创建数据库和表结构：

```sql
CREATE DATABASE IF NOT EXISTS drone_db DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE drone_db;

CREATE TABLE `drone_photos` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `filename` VARCHAR(255) DEFAULT NULL COMMENT '文件名',
  `FolderName` VARCHAR(255) DEFAULT NULL COMMENT '来源项目/文件夹',
  `FileHash` VARCHAR(32) DEFAULT NULL COMMENT 'MD5指纹',
  `FileSize` BIGINT(20) DEFAULT NULL,
  `capture_time` DATETIME DEFAULT NULL,
  `created_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- 设备信息
  `DroneModel` VARCHAR(100) DEFAULT NULL,
  `DroneSerialNumber` VARCHAR(100) DEFAULT NULL,
  `CameraSerialNumber` VARCHAR(100) DEFAULT NULL,
  `Version` VARCHAR(50) DEFAULT NULL,
  `ImageSource` VARCHAR(50) DEFAULT NULL,
  
  -- 定位与高度
  `GpsStatus` VARCHAR(50) DEFAULT NULL,
  `AltitudeType` VARCHAR(50) DEFAULT NULL,
  `GpsLatitude` DOUBLE DEFAULT NULL,
  `GpsLongitude` DOUBLE DEFAULT NULL,
  `AbsoluteAltitude` FLOAT DEFAULT NULL,
  `RelativeAltitude` FLOAT DEFAULT NULL,
  
  -- 姿态与速度
  `GimbalRollDegree` FLOAT DEFAULT NULL,
  `GimbalYawDegree` FLOAT DEFAULT NULL,
  `GimbalPitchDegree` FLOAT DEFAULT NULL,
  `FlightRollDegree` FLOAT DEFAULT NULL,
  `FlightYawDegree` FLOAT DEFAULT NULL,
  `FlightPitchDegree` FLOAT DEFAULT NULL,
  `FlightXSpeed` FLOAT DEFAULT NULL,
  `FlightYSpeed` FLOAT DEFAULT NULL,
  `FlightZSpeed` FLOAT DEFAULT NULL,
  
  -- RTK & LRF
  `RtkFlag` INT(11) DEFAULT NULL,
  `RtkStdLon` FLOAT DEFAULT NULL,
  `RtkStdLat` FLOAT DEFAULT NULL,
  `RtkStdHgt` FLOAT DEFAULT NULL,
  `LRFStatus` VARCHAR(50) DEFAULT NULL,
  `LRFTargetDistance` FLOAT DEFAULT NULL,
  `LRFTargetLon` FLOAT DEFAULT NULL,
  `LRFTargetLat` FLOAT DEFAULT NULL,
  `LRFTargetAlt` FLOAT DEFAULT NULL,
  `LRFTargetAbsAlt` FLOAT DEFAULT NULL,
  `SurveyingMode` VARCHAR(50) DEFAULT NULL,
  `FlightLineInfo` VARCHAR(100) DEFAULT NULL,
  `CamReverse` TINYINT(1) DEFAULT 0,
  `GimbalReverse` TINYINT(1) DEFAULT 0,

  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_file_hash` (`FileHash`),
  KEY `idx_capture_time` (`capture_time`),
  KEY `idx_folder_name` (`FolderName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='无人机航拍元数据表';
```

### 4. 配置文件 

（1）直接修改

请直接修改app.py中的如下配置区域

```python
DB_CONFIG = {   # 根据本地数据库配置
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'drone_photos'
}
API_KEY =  ""                           # 填入自己的key
API_BASE = "https://api.deepseek.com"   # 以deepseek为例
```

其中，DB_CONFIG需要与本地数据库的格式相对应。API_KEY需要自己前往https://platform.deepseek.com/api_keys进行创建，也可以使用其他模型。

（2）安全配置

为了安全起见，不直接修改 `app.py` 中的密码，而是在项目根目录下创建一个名为 `.streamlit` 的文件夹，并在其中新建 `secrets.toml` 文件：

**文件路径**: `.streamlit/secrets.toml`

```
[mysql]
host = "127.0.0.1"
user = "root"
password = "YOUR_MYSQL_PASSWORD"  # 替换为你的数据库密码
database = "drone_db"
```

### 5. 启动应用

在终端运行以下命令：

**本地运行：**

Bash

```
streamlit run app.py
```

**局域网共享模式（让同事访问）：**

Bash

```
streamlit run app.py --server.address=0.0.0.0
```

启动后，控制台会显示 `Network URL` (例如 `http://192.168.1.5:8501`)，将该地址发送给局域网内的设备即可访问。



------

## 📖 操作指南

### 1. 📂 文件夹批量入库

1. 切换到左侧菜单的 **“文件夹批量入库”**。
2. 输入存放照片的**绝对路径** (例如 `D:\Photos\Project_A` 或 NAS 路径)。
3. 对于使用NAS的情况，推荐将网络驱动器映射到本地（如Z盘）后，直接使用其路径
4. 点击 **“开始扫描并入库”**。系统会自动去重，已存在的照片会自动跳过。

### 2. 📊 数据展示与查询

1. 使用侧边栏筛选器：支持按日期、机型、RTK 固定解状态进行过滤。
2. **高级筛选**: 在页面中部选择具体属性（如“绝对高度”），设定数值范围（如 100m ~ 500m）。
3. 点击 **“导出数据 (CSV)”** 可将筛选结果下载为表格。
4. 点击 **“同步筛选结果到地图”**，将当前列表的数据发送到地图模块。

### 3. 🧠 数据库实验室 (AI 功能)

1. 切换到 **“AI 智能辅助”** 模式。

2. 输入 DeepSeek API Key (需自行申请)。

3. 在聊天框输入中文指令，例如：

   > "帮我统计每个项目的照片数量" "列出所有激光测距距离大于 200 米的照片"

4. AI 将自动生成 SQL 并执行查询，结果可直接下载。

------



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