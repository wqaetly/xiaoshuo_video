# 小说转视频生成系统

基于混合方案的小说转视频自动化生成框架，将小说文本自动转换为带配音和字幕的视频。

## 技术架构

| 模块 | 技术 | 说明 |
|------|------|------|
| LLM分镜 | Ollama + GLM-4-9B | 智能分镜、角色提取 |
| 图像生成 | ComfyUI + Z-Image-Turbo | 场景图、角色设计 (4步快速生成) |
| 角色一致性 | Z-Image-i2L | 从参考图即时生成角色 LoRA |
| 视频生成 | Wan 2.1 / 即梦AI / 可灵AI | 本地 I2V 或远端 API |
| TTS配音 | CosyVoice / Edge TTS | 语音合成 |
| 视频合成 | FFmpeg | 视频拼接、字幕叠加 |
| Web界面 | React + Ant Design | 可视化项目管理 |
| API后端 | FastAPI + WebSocket | REST API + 实时通信 |

## 系统要求

- **显卡**: RTX 3080 10GB+ (推荐 RTX 5080 16GB)
- **内存**: 16GB+ (推荐 32GB)
- **Python**: 3.10+
- **CUDA**: 11.8+

## 快速开始

### 1. 安装
```powershell
.\setup.bat
```

### 2. 启动
```powershell
.\start_react_webui.bat
```

### 3. 访问
- Web界面: http://localhost:5173
- API文档: http://localhost:8000/docs

## 处理流程

```
小说文本 → 分镜生成 → 角色设计 → 场景图像 → 语音合成 → 视频生成 → 最终合成
         (Ollama)   (ComfyUI)  (Z-Image)   (TTS)    (Wan/API)   (FFmpeg)
```

## 项目结构

```
├── src/          # 核心模块 (llm/image/video/tts/compose/pipeline)
├── api/          # FastAPI 后端
├── web/          # React 前端
├── config/       # 配置文件 (settings.yaml, prompts/, workflows/)
├── data/         # 项目数据
└── scripts/      # 工具脚本
```

## 依赖服务

| 服务 | 默认地址 | 用途 |
|------|----------|------|
| Ollama | localhost:11434 | LLM分镜 |
| ComfyUI | localhost:8188 | 图像/视频生成 |
| CosyVoice | localhost:9880 | TTS语音 |

## 命令行使用

```powershell
# 创建项目
python -m src.main create --name "项目名" --novel "小说.txt"

# 运行生成
python -m src.main run --project "项目名"

# 断点续传
python -m src.main run --project "项目名" --resume
```

## 配置

环境变量 (`.env`):
```bash
JIMENG_API_KEY=xxx    # 即梦API (可选)
KLING_API_KEY=xxx     # 可灵API (可选)
```

详细配置见 `config/settings.yaml`

## License

MIT License
