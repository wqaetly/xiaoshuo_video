# 小说转视频生成系统

基于混合方案的小说转视频自动化生成框架。

## 技术架构

| 模块 | 技术 | 部署方式 |
|------|------|----------|
| LLM分镜 | Ollama + Qwen2.5-14B | 本地 |
| 图像生成 | ComfyUI + SDXL | 本地 |
| 视频生成 | 即梦AI / 可灵AI | 远端API |
| TTS配音 | CosyVoice | 本地 |
| 视频合成 | FFmpeg | 本地 |

## 快速开始

### 1. 环境安装

```powershell
# 运行安装脚本
.\scripts\setup_env.ps1

# 或手动安装
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，填入视频API密钥
```

### 3. 启动服务

```powershell
# 启动本地服务 (Ollama, ComfyUI, CosyVoice)
.\scripts\start_services.ps1
```

### 4. 使用

**Web界面 (推荐)**:
```bash
python -m src.main ui
# 访问 http://127.0.0.1:7860
```

**命令行**:
```bash
# 创建项目
python -m src.main create --name "我的小说" --novel "path/to/novel.txt"

# 运行生成
python -m src.main run --project "我的小说"

# 断点续传
python -m src.main run --project "我的小说" --resume

# 查看状态
python -m src.main status --project "我的小说"
```

## 项目结构

```
xiaoshuo_video/
├── src/                    # 源代码
│   ├── llm/               # LLM模块 (分镜生成)
│   ├── image/             # 图像模块 (ComfyUI)
│   ├── video/             # 视频API模块
│   ├── tts/               # TTS模块 (CosyVoice)
│   ├── compose/           # 视频合成模块
│   ├── pipeline/          # 流程控制
│   ├── utils/             # 工具类
│   ├── main.py            # CLI入口
│   └── webui.py           # Web界面
├── config/                 # 配置文件
│   ├── settings.yaml      # 全局设置
│   └── prompts/           # LLM提示词
├── data/projects/          # 项目数据
├── scripts/                # 脚本
└── requirements.txt
```

## 处理流程

```
小说文本 → 分镜生成 → 角色设计 → 图像生成 → 音频生成 → 视频生成 → 合成输出
   │          │          │          │          │          │
   │       (本地LLM)  (本地ComfyUI) (本地)    (本地TTS)  (远端API)
   │          │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┴──────────┘
                              ↓
                        最终视频 + 字幕
```

## 配置说明

### config/settings.yaml

```yaml
local:
  ollama_url: "http://localhost:11434"
  ollama_model: "qwen2.5:14b"
  comfyui_url: "http://localhost:8188"
  cosyvoice_url: "http://localhost:9880"

api:
  video_provider: "jimeng"  # jimeng / kling
  use_idle_time: true       # 使用闲时折扣

video:
  resolution: "1280x720"
  fps: 24
  style: "anime"
```

## 依赖服务

1. **Ollama** - https://ollama.com/
   ```bash
   ollama pull qwen2.5:14b
   ```

2. **ComfyUI** - https://github.com/comfyanonymous/ComfyUI

3. **CosyVoice** - https://github.com/FunAudioLLM/CosyVoice

4. **FFmpeg** - https://ffmpeg.org/

## 成本估算

```
单个5分钟视频:
├── LLM分镜: ¥0 (本地)
├── 图像生成: ¥0 (本地)
├── 视频生成: ¥60-180 (即梦API)
├── TTS配音: ¥0 (本地)
└── 总计: ¥60-180/视频
```

## License

MIT
