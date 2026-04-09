# CLAUDE.md - 项目开发指引

## 项目概述

小说转视频自动化生成系统。将小说文本 → 分镜 → 角色设计 → 场景图像 → 语音合成 → 视频生成 → 最终合成。

**架构**: 混合方案 = 本地服务 (LLM/图像/TTS) + 远端API (视频生成)

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, WebSocket, Pydantic |
| 前端 | React 19, TypeScript, Ant Design 6, Vite 7, Zustand |
| LLM | Ollama + GLM-4-9B |
| 图像 | ComfyUI + Z-Image-Turbo (4步快速生成) |
| 视频 | 即梦AI / 可灵AI (远端API) + 本地 Wan 2.1 |
| TTS | CosyVoice / Edge TTS |
| 合成 | FFmpeg |

## 目录结构

```
src/                    # Python 核心模块
  llm/                  # LLM 分镜生成 (Ollama 客户端、角色提取、分镜生成)
  image/                # 图像生成 (ComfyUI 客户端、场景生成、角色设计)
  video/                # 视频生成 (即梦/可灵/Wan API 客户端)
  tts/                  # 语音合成 (CosyVoice/Edge TTS)
  compose/              # FFmpeg 视频合成 (拼接/字幕/音频混合)
  pipeline/             # 流程控制 (主控制器/状态管理/并行调度/阶段执行)
  generators/           # 统一生成器接口 (工厂模式 + capabilities 能力注册)
  audio/                # 音频分析
  utils/                # 工具 (配置/日志/文件/重试/GPU监控)
  main.py               # CLI 入口

api/                    # FastAPI 后端
  main.py               # FastAPI 应用入口
  models/               # Pydantic 请求/响应模型
  routers/              # API 路由 (projects/scenes/characters/generation/tasks/editor/settings/files)
  services/             # 业务逻辑 (含 task_queue 任务队列系统)
  websocket/            # WebSocket 实时日志推送

web/src/                # React 前端
  api/                  # Axios API 客户端 + WebSocket
  pages/                # 页面 (Projects/Scenes/Characters/Generation/Preview/Settings/Tasks/Editor)
  components/           # 组件 (Timeline/VideoPlayer/SubTaskProgress)
  hooks/                # 自定义 hooks (useTaskEvents)
  layouts/              # 布局 (MainLayout)
  types/                # TypeScript 类型

config/                 # 配置
  settings.yaml         # 全局配置
  capabilities.yaml     # 模型能力定义
  prompts/              # LLM 提示词模板
  comfyui_workflows/    # ComfyUI 工作流 JSON
```

## 开发规范

- **Python**: type hints, loguru 日志, asyncio + httpx 异步, Pydantic 数据验证
- **命名**: 文件 `snake_case.py`, 类 `PascalCase`, 函数/变量 `snake_case`, 常量 `UPPER_CASE`
- **中文注释**: 函数和类使用中文注释说明功能
- **配置**: 统一通过 `config/settings.yaml` + `.env` 环境变量管理
- **错误处理**: 使用 loguru 记录, API 调用需重试机制, 断点续传持久化到 `data/projects/`
- **代码格式**: Ruff (line-length=100), 双引号字符串

## 常用命令

```bash
# 启动 (一键)
./start_react_webui.bat

# 分别启动
uvicorn api.main:app --reload --port 8000    # API 后端
cd web && npm run dev                         # React 前端

# CLI
python -m src.main create --name "项目名" --novel "小说.txt"
python -m src.main run --project "项目名" --resume

# 测试
pytest
pytest -x --tb=short

# Lint
ruff check src/ api/
ruff format src/ api/
```

## 外部服务

| 服务 | 地址 | 用途 |
|---|---|---|
| Ollama | localhost:11434 | LLM 分镜 |
| ComfyUI | localhost:8188 | 图像生成 |
| CosyVoice | localhost:9880 | TTS 语音 |
| FastAPI | localhost:8000 | API 后端 |
| Vite Dev | localhost:5173 | 前端开发 |

## API 路由

所有路由前缀 `/api`:
- `/api/projects` - 项目 CRUD
- `/api/scenes` - 分镜场景
- `/api/characters` - 角色管理
- `/api/generation` - 生成控制 (启动/停止/进度)
- `/api/tasks` - 任务队列
- `/api/editor` - 视频编辑
- `/api/settings` - 系统设置
- `/api/files` - 文件管理
- `/api/ws` - WebSocket (实时日志/进度)

## Pipeline 阶段

INIT → ANALYZE (角色提取+分镜) → CHARACTER_DESIGN → GENERATE_IMAGES → GENERATE_AUDIO → GENERATE_VIDEO → COMPOSE → DONE

支持断点续传，状态持久化到 `pipeline_state.json`。

## 关键数据文件 (每个项目)

- `data/projects/{name}/storyboard.json` - 分镜数据
- `data/projects/{name}/characters.json` - 角色数据
- `data/projects/{name}/pipeline_state.json` - 状态
- `data/projects/{name}/project.yaml` - 项目配置

## 注意事项

- API 密钥只放 `.env`，不提交到 Git
- 生成的视频/模型文件不提交到 Git
- 视频生成 API 为异步，需轮询获取结果
- 注意显存占用，ComfyUI 可能需要 `--lowvram`
- 前端路由: `/projects/:projectName/scenes|characters|generation|preview|editor`
