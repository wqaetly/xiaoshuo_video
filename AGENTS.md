# 小说转视频生成系统 - AI 开发指引

## 项目概述

基于混合方案的小说转视频自动化生成框架，将小说文本自动转换为带配音和字幕的视频。

## 技术栈

- **语言**: Python 3.10+
- **LLM**: Ollama + GLM-4-9B
- **图像生成**: ComfyUI + Z-Image-Turbo (阿里通义6B参数，4步快速生成，中文优化)
- **视频生成**: 即梦AI / 可灵AI (远端API)
- **TTS**: CosyVoice / Edge TTS
- **视频合成**: FFmpeg
- **Web界面**: React + Ant Design + TypeScript
- **API后端**: FastAPI + WebSocket

## 项目结构

```
src/
├── llm/          # LLM模块 - 分镜生成、角色提取
├── image/        # 图像模块 - ComfyUI场景图/角色设计
├── video/        # 视频API模块 - 即梦/可灵
├── tts/          # TTS模块 - CosyVoice语音合成
├── compose/      # 视频合成模块 - FFmpeg拼接
├── pipeline/     # 流程控制 - 主控制器、状态管理
├── utils/        # 工具类
└── main.py       # CLI入口

api/
├── main.py       # FastAPI 应用入口
├── models/       # Pydantic 数据模型
├── routers/      # API 路由
├── services/     # 业务逻辑服务
└── websocket/    # WebSocket 实时日志

web/
├── src/
│   ├── api/      # API 客户端
│   ├── pages/    # 页面组件
│   ├── components/  # 通用组件
│   └── types/    # TypeScript 类型定义
└── package.json

config/
├── settings.yaml       # 全局配置
├── prompts/            # LLM提示词模板
└── comfyui_workflows/  # ComfyUI工作流JSON
```

## 开发规范

### 代码风格
- 使用 Python type hints
- 函数和类使用中文注释说明功能
- 异步操作优先使用 `asyncio` + `httpx`
- 配置统一通过 `config/settings.yaml` 和环境变量管理

### 命名约定
- 文件名: 小写下划线 (`scene_generator.py`)
- 类名: 大驼峰 (`SceneGenerator`)
- 函数/变量: 小写下划线 (`generate_scene`)
- 常量: 大写下划线 (`MAX_RETRY_COUNT`)

### 错误处理
- 使用 `loguru` 记录日志
- API调用需要重试机制
- 支持断点续传，状态持久化到 `data/projects/`

### 依赖管理
- 核心依赖在 `requirements.txt`
- 新增依赖需同步更新 requirements.txt
- 使用 pydantic 进行数据验证

## 常用命令

```bash
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 启动 WebUI
start_react_webui.bat
# 或分别启动后端和前端
uvicorn api.main:app --reload --port 8000  # API 后端
cd web && npm run dev                       # React 前端

# CLI 使用
python -m src.main create --name "项目名" --novel "小说路径"
python -m src.main run --project "项目名"
python -m src.main run --project "项目名" --resume  # 断点续传
```

## 外部服务依赖

| 服务 | 默认地址 | 用途 |
|------|----------|------|
| Ollama | http://localhost:11434 | LLM分镜生成 |
| ComfyUI | http://localhost:8188 | 图像生成 |
| CosyVoice | http://localhost:9880 | TTS语音合成 |

## MCP 工具使用指引

项目配置了 mcp-router，可使用以下 MCP 工具辅助开发：

### Context7 (文档查询)
查询第三方库的最新文档和 API 用法。遇到不确定，不认识的API需求时，请必须使用context7进行查询

```
# 先解析库 ID
resolve-library-id: fastapi

# 再查询文档
get-library-docs: /tiangolo/fastapi, topic="WebSocket"
```

**适用场景**: 查询 FastAPI、React、Ant Design、Pydantic、httpx 等依赖库的 API 文档

### Codex (代码执行)
在隔离环境中执行代码任务。

```
codex: PROMPT="分析 src/pipeline 目录结构", cd="E:\Study\wqaetly\xiaoshuo_video"
```

**适用场景**:
- 代码分析和重构建议
- 批量文件操作
- 复杂的代码生成任务

### 使用建议

1. **文档查询优先用 Context7**: 比搜索引擎更精准，直接获取 API 示例
2. **Codex 用于隔离任务**: 需要独立环境执行的代码任务

## 注意事项

1. **API密钥安全**: 密钥只存放在 `.env` 文件，不要提交到版本控制
2. **大文件**: 模型文件、生成的视频不要提交到 Git
3. **异步处理**: 视频生成API为异步，需要轮询获取结果
4. **资源管理**: 注意显存占用，ComfyUI 可能需要 `--lowvram` 模式
