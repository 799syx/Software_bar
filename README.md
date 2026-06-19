# 灵山胜境 AI 数字人导览系统

本项目对应“景区导览服务 AI 数字人”方向，包含 Vue 3 游客端/管理端、Python 标准库后端、SQLite 本地资料库、官方公开资料包导入、问答/RAG、图片讲解、语音播报、路线推荐、扫码/定位和运营看板。

## 主要功能

- 游客端数字人问答、景点详情、路线推荐、图片讲解和语音输入/播报。
- 地图导览支持景区示意图、高德底图、点位码校准和 GPS 附近景点推荐。
- 管理端支持景点、知识库、数字人配置、低置信问答沉淀、运营概览和体验报告。
- 后端启动时会从内置种子数据和 `示范景区公开资料包/` 自动初始化 SQLite 数据库。
- 大模型接口使用 OpenAI 兼容 `/chat/completions`，默认推荐 DashScope Qwen3-VL。

## 目录结构

```text
backend/                 Python 后端 API
backend/routes/          HTTP 路由表与请求处理
backend/data/            运行时数据库目录，交付时默认排除
frontend-vue/            Vue 3 主前端
frontend-mobile/         独立移动端入口
docs/                    设计、部署、测试和交付文档
scripts/                 清理与交付脚本
tests/                   后端单元/HTTP 回归测试
示范景区公开资料包/       官方公开资料与行为样本
```

## 快速启动

1. 复制环境配置：

```bat
copy .env.example .env
```

2. 填写 `.env` 中的 `DASHSCOPE_API_KEY` 和 `SCENIC_ADMIN_TOKEN`。

3. 一键启动演示：

```bat
start_demo.bat
```

常用地址：

```text
后端 API: http://127.0.0.1:8000
Vue 前端: http://127.0.0.1:5173
移动端:   http://127.0.0.1:8000/mobile/
```

弱网或答辩现场只想使用本地资料快速回答时：

```bat
start_demo.bat --fast
```

## 手动运行

后端：

```bat
python backend/app.py
```

如果当前终端没有 `python`，可以使用项目脚本自动查找本机 Python：

```bat
run_server.bat
```

前端：

```bat
cd frontend-vue
npm install
npm run dev
```

生产构建：

```bat
cd frontend-vue
npm run build
```

## 测试

后端回归：

```bat
python -m unittest discover -s tests
```

前端类型检查、单测和构建：

```bat
cd frontend-vue
npm run typecheck
npm run test:unit
npm run build
```

## 交付打包

默认生成干净源码包，不包含 `.env`、`node_modules`、`dist`、临时目录或运行数据库：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_delivery.ps1
```

输出目录为 `delivery/`。默认数据库策略是“启动重建”：老师或评审解压后按快速启动步骤运行，后端会自动生成 `backend/data/scenic_guide.db`。

如确实需要演示带库包，可显式执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_delivery.ps1 -IncludeDemoDatabase
```

## 安全说明

`.env` 和任何真实 API Key 都不得提交或放入交付包。若 Key 曾经公开暴露，应在对应平台后台吊销并重新生成。本轮按用户要求不处理 Key 轮换，但交付脚本和 `.gitignore` 会默认排除本机密钥文件。
