# 小说转视频生成系统

基于混合方案的小说转视频自动化生成框架，将小说文本自动转换为带配音和字幕的视频。

## 技术架构

| 模块 | 技术 | 部署方式 | 说明 |
|------|------|----------|------|
| LLM分镜 | Ollama + Qwen2.5-14B | 本地 | 智能分镜、角色提取 |
| 图像生成 | ComfyUI + SDXL | 本地 | 场景图、角色设计图 |
| 视频生成 | 即梦AI / 可灵AI | 远端API | 图生视频 |
| TTS配音 | CosyVoice | 本地 | 语音合成 |
| 视频合成 | FFmpeg | 本地 | 视频拼接、字幕叠加 |

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8核 | 16核+ |
| 内存 | 16GB | 32GB+ |
| 显卡 | GTX 1060 6GB | RTX 3080 10GB+ |
| 硬盘 | 50GB可用空间 | 200GB+ SSD |

> **注意**: ComfyUI运行SDXL模型需要至少8GB显存，建议使用NVIDIA显卡。

### 软件要求

- **操作系统**: Windows 10/11 或 Linux
- **Python**: 3.10 或更高版本
- **CUDA**: 11.8+ (NVIDIA显卡用户)
- **Git**: 用于克隆项目

---

## 一、基础环境安装

### 1.1 安装Python

1. 下载 [Python 3.10+](https://www.python.org/downloads/)
2. 安装时勾选 "Add Python to PATH"
3. 验证安装：
   ```powershell
   python --version
   # 输出: Python 3.10.x 或更高
   ```

### 1.2 克隆项目

```powershell
git clone https://github.com/your-repo/xiaoshuo_video.git
cd xiaoshuo_video
```

### 1.3 创建虚拟环境并安装依赖

**方式一：使用安装脚本 (推荐)**
```powershell
.\scripts\setup_env.ps1
```

**方式二：手动安装**
```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

---

## 二、依赖服务安装

### 2.1 Ollama (LLM服务)

Ollama用于运行本地大语言模型，负责分镜生成和角色提取。

#### 安装步骤

1. **下载Ollama**
   - 访问 [https://ollama.com/download](https://ollama.com/download)
   - 下载Windows版安装包并安装

2. **验证安装**
   ```powershell
   ollama --version
   # 输出: ollama version x.x.x
   ```

3. **下载模型**
   ```powershell
   # 下载Qwen2.5-14B模型 (约9GB)
   ollama pull qwen2.5:14b

   # 也可以使用较小的模型 (显存不足时)
   ollama pull qwen2.5:7b
   ```

4. **启动服务**
   ```powershell
   ollama serve
   # 服务运行在 http://localhost:11434
   ```

5. **测试服务**
   ```powershell
   # 新开一个终端窗口
   curl http://localhost:11434/api/tags
   # 应返回已安装的模型列表
   ```

#### 常见问题

- **端口占用**: 如果11434端口被占用，设置环境变量 `OLLAMA_HOST=0.0.0.0:11435`
- **模型下载慢**: 设置代理 `set HTTPS_PROXY=http://127.0.0.1:7890`

---

### 2.2 ComfyUI (图像生成)

ComfyUI是基于节点的Stable Diffusion图像生成工具。

#### 安装步骤

1. **克隆ComfyUI**
   ```powershell
   # 在项目根目录执行
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   ```

2. **安装依赖**
   ```powershell
   # 创建虚拟环境 (可选，推荐)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # 安装PyTorch (CUDA 11.8)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

   # 或 CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

   # 安装其他依赖
   pip install -r requirements.txt
   ```

3. **下载模型**

   需要下载SDXL基础模型放到 `ComfyUI/models/checkpoints/` 目录：

   | 模型 | 下载地址 | 说明 |
   |------|----------|------|
   | SDXL Base | [Hugging Face](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 必需，约6.5GB |
   | SDXL Refiner | [Hugging Face](https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0) | 可选，提升细节 |

   **下载命令** (需要安装huggingface-cli):
   ```powershell
   pip install huggingface_hub

   # 下载SDXL Base模型
   huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir ComfyUI/models/checkpoints/
   ```

   **或手动下载**:
   - 访问 [https://civitai.com/models/101055](https://civitai.com/models/101055) 下载SDXL模型
   - 将 `.safetensors` 文件放入 `ComfyUI/models/checkpoints/`

4. **启动ComfyUI**
   ```powershell
   cd ComfyUI
   python main.py
   # 服务运行在 http://localhost:8188
   ```

5. **验证安装**
   - 打开浏览器访问 [http://localhost:8188](http://localhost:8188)
   - 应看到ComfyUI的节点编辑界面

#### 推荐的额外模型

放入对应目录即可使用：

| 类型 | 目录 | 推荐模型 |
|------|------|----------|
| VAE | `models/vae/` | sdxl_vae.safetensors |
| LoRA | `models/loras/` | 各种风格LoRA |
| ControlNet | `models/controlnet/` | 用于姿态控制 |

#### 常见问题

- **显存不足**: 启动时添加参数 `python main.py --lowvram`
- **生成慢**: 启用xformers加速 `pip install xformers`
- **模型加载失败**: 检查模型文件是否完整，重新下载

---

### 2.3 CosyVoice (语音合成)

CosyVoice是阿里开源的语音合成模型，支持中文和多种音色。

#### 安装步骤

1. **克隆CosyVoice**
   ```powershell
   # 在项目根目录执行
   git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
   cd CosyVoice
   ```

2. **安装依赖**
   ```powershell
   # 创建虚拟环境
   conda create -n cosyvoice python=3.10
   conda activate cosyvoice

   # 安装PyTorch
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

   # 安装其他依赖
   pip install -r requirements.txt
   ```

3. **下载预训练模型**

   模型会在首次运行时自动下载，也可以手动下载：
   ```powershell
   # 安装modelscope
   pip install modelscope

   # 下载模型 (约2GB)
   python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice-300M')"
   ```

4. **启动API服务**

   创建API服务文件 `CosyVoice/api.py`:
   ```python
   from fastapi import FastAPI
   from cosyvoice.cli.cosyvoice import CosyVoice
   import uvicorn

   app = FastAPI()
   cosyvoice = CosyVoice('pretrained_models/CosyVoice-300M')

   @app.post("/tts")
   async def tts(text: str, speaker: str = "中文女"):
       output = cosyvoice.inference_sft(text, speaker)
       return {"audio": output}

   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=9880)
   ```

   启动服务:
   ```powershell
   cd CosyVoice
   python api.py
   # 服务运行在 http://localhost:9880
   ```

#### 备选方案

如果CosyVoice安装困难，可以考虑：
- **Edge-TTS**: 微软在线TTS，无需本地部署
- **GPT-SoVITS**: 另一个开源语音合成方案

---

### 2.4 FFmpeg (视频处理)

FFmpeg用于视频合成、格式转换、字幕叠加等。

#### Windows安装

1. **下载FFmpeg**
   - 访问 [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
   - 下载 `ffmpeg-release-essentials.zip`

2. **解压并配置环境变量**
   ```powershell
   # 解压到某个目录，例如 C:\ffmpeg
   # 将 C:\ffmpeg\bin 添加到系统PATH环境变量
   ```

3. **验证安装**
   ```powershell
   ffmpeg -version
   # 输出: ffmpeg version x.x.x ...
   ```

#### 使用Chocolatey安装 (推荐)

```powershell
# 安装Chocolatey (如果没有)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装FFmpeg
choco install ffmpeg
```

---

## 三、视频API配置

本项目使用第三方API进行图生视频，需要申请API密钥。

### 3.1 即梦AI (推荐)

即梦AI是字节跳动旗下的视频生成平台。

1. **注册账号**
   - 访问 [https://jimeng.jianying.com](https://jimeng.jianying.com)
   - 使用手机号或抖音账号登录

2. **获取API密钥**
   - 进入开发者中心
   - 创建应用，获取API Key

3. **配置密钥**
   ```bash
   # 编辑 .env 文件
   JIMENG_API_KEY=your_api_key_here
   ```

### 3.2 可灵AI (备选)

可灵AI是快手旗下的视频生成平台。

1. **注册账号**
   - 访问 [https://klingai.kuaishou.com](https://klingai.kuaishou.com)
   - 使用手机号注册

2. **获取API密钥**
   - 进入开发者后台
   - 申请API访问权限

3. **配置密钥**
   ```bash
   # 编辑 .env 文件
   KLING_API_KEY=your_api_key_here
   ```

4. **切换视频提供商**
   ```yaml
   # 编辑 config/settings.yaml
   api:
     video_provider: "kling"  # 从 jimeng 改为 kling
   ```

---

## 四、配置说明

### 4.1 环境变量 (.env)

```bash
# 复制模板文件
copy .env.example .env
```

编辑 `.env` 文件：
```bash
# 视频API密钥 (必填，选择一个)
JIMENG_API_KEY=your_jimeng_api_key_here
KLING_API_KEY=your_kling_api_key_here

# 自定义服务地址 (可选)
OLLAMA_URL=http://localhost:11434
COMFYUI_URL=http://localhost:8188
COSYVOICE_URL=http://localhost:9880
```

### 4.2 全局设置 (config/settings.yaml)

```yaml
# 视频参数
video:
  resolution: "1280x720"  # 分辨率: 1280x720 / 1920x1080
  fps: 24                  # 帧率
  style: "anime"           # 风格: anime / realistic / illustration

# 本地服务配置
local:
  ollama_url: "http://localhost:11434"
  ollama_model: "qwen2.5:14b"  # 可改为 qwen2.5:7b
  comfyui_url: "http://localhost:8188"
  cosyvoice_url: "http://localhost:9880"

# API配置
api:
  video_provider: "jimeng"  # jimeng / kling
  use_idle_time: true       # 使用闲时折扣 (成本更低)

# 生成参数
generation:
  scene_duration_min: 3.0   # 最短场景时长 (秒)
  scene_duration_max: 6.0   # 最长场景时长 (秒)
  max_concurrent_tasks: 3   # 最大并发任务数
  retry_count: 3            # 失败重试次数
```

---

## 五、启动和使用

### 5.1 启动所有服务

**方式一：使用启动脚本**
```powershell
.\scripts\start_services.ps1
```

**方式二：手动启动**

打开4个终端窗口分别执行：

```powershell
# 终端1: Ollama
ollama serve

# 终端2: ComfyUI
cd ComfyUI
python main.py

# 终端3: CosyVoice
cd CosyVoice
conda activate cosyvoice
python api.py

# 终端4: 主程序
cd xiaoshuo_video
.\venv\Scripts\Activate.ps1
python -m src.main ui
```

### 5.2 服务状态检查

确保所有服务正常运行：

| 服务 | 地址 | 检查方式 |
|------|------|----------|
| Ollama | http://localhost:11434 | 浏览器访问，显示 "Ollama is running" |
| ComfyUI | http://localhost:8188 | 浏览器访问，显示节点编辑界面 |
| CosyVoice | http://localhost:9880 | 浏览器访问API文档 |

### 5.3 使用Web界面 (推荐)

```powershell
python -m src.main ui
```

访问 [http://127.0.0.1:7860](http://127.0.0.1:7860)

Web界面功能：
- 上传小说文件或粘贴文本
- 实时预览分镜结果
- 查看生成进度
- 下载最终视频

### 5.4 命令行使用

```powershell
# 创建新项目
python -m src.main create --name "我的小说" --novel "path/to/novel.txt"

# 运行完整生成流程
python -m src.main run --project "我的小说"

# 断点续传 (中断后继续)
python -m src.main run --project "我的小说" --resume

# 查看项目状态
python -m src.main status --project "我的小说"

# 仅执行某个步骤
python -m src.main run --project "我的小说" --step storyboard  # 分镜
python -m src.main run --project "我的小说" --step image       # 图像
python -m src.main run --project "我的小说" --step video       # 视频
python -m src.main run --project "我的小说" --step tts         # 配音
python -m src.main run --project "我的小说" --step compose     # 合成
```

---

## 六、处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         小说文本输入                              │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [1] 分镜生成 (Ollama)                                           │
│  - 解析小说章节                                                   │
│  - 提取场景描述                                                   │
│  - 生成分镜脚本                                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [2] 角色设计 (ComfyUI)                                          │
│  - 提取角色信息                                                   │
│  - 生成角色设计图                                                 │
│  - 保持角色一致性                                                 │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [3] 场景图像生成 (ComfyUI)                                      │
│  - 基于分镜生成场景图                                             │
│  - 融入角色形象                                                   │
│  - 保持风格统一                                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [4] 语音合成 (CosyVoice)                                        │
│  - 生成旁白配音                                                   │
│  - 角色对话语音                                                   │
│  - 匹配场景时长                                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [5] 视频生成 (即梦/可灵API)                                      │
│  - 图生视频                                                       │
│  - 添加动态效果                                                   │
│  - 批量处理                                                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  [6] 视频合成 (FFmpeg)                                           │
│  - 拼接视频片段                                                   │
│  - 叠加配音                                                       │
│  - 添加字幕                                                       │
│  - 输出最终视频                                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      最终视频 + 字幕文件                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、项目结构

```
xiaoshuo_video/
├── src/                        # 源代码
│   ├── llm/                    # LLM模块
│   │   ├── client.py           # Ollama客户端
│   │   ├── storyboard_generator.py  # 分镜生成
│   │   └── character_extractor.py   # 角色提取
│   ├── image/                  # 图像模块
│   │   ├── comfyui_client.py   # ComfyUI客户端
│   │   ├── scene_generator.py  # 场景图生成
│   │   └── character_designer.py    # 角色设计
│   ├── video/                  # 视频API模块
│   │   ├── api_client.py       # 通用API客户端
│   │   ├── jimeng.py           # 即梦AI
│   │   └── kling.py            # 可灵AI
│   ├── tts/                    # TTS模块
│   │   ├── cosyvoice_client.py # CosyVoice客户端
│   │   └── voice_manager.py    # 语音管理
│   ├── compose/                # 视频合成模块
│   │   ├── video_composer.py   # 视频合成器
│   │   ├── audio_mixer.py      # 音频混合
│   │   └── subtitle.py         # 字幕生成
│   ├── pipeline/               # 流程控制
│   │   ├── controller.py       # 主控制器
│   │   └── state.py            # 状态管理
│   ├── utils/                  # 工具类
│   ├── main.py                 # CLI入口
│   └── webui.py                # Web界面
├── config/                     # 配置文件
│   ├── settings.yaml           # 全局设置
│   └── prompts/                # LLM提示词模板
├── data/                       # 数据目录
│   └── projects/               # 项目数据存储
├── scripts/                    # 脚本
│   ├── setup_env.ps1           # 环境安装
│   └── start_services.ps1      # 服务启动
├── ComfyUI/                    # ComfyUI (需手动安装)
├── CosyVoice/                  # CosyVoice (需手动安装)
├── .env                        # 环境变量 (需创建)
├── .env.example                # 环境变量模板
├── requirements.txt            # Python依赖
└── README.md                   # 说明文档
```

---

## 八、成本估算

### 本地运行成本

| 组件 | 成本 |
|------|------|
| LLM分镜 (Ollama) | 免费 (电费) |
| 图像生成 (ComfyUI) | 免费 (电费) |
| TTS配音 (CosyVoice) | 免费 (电费) |
| 视频合成 (FFmpeg) | 免费 |

### 视频API成本

| 平台 | 正常价格 | 闲时价格 | 说明 |
|------|----------|----------|------|
| 即梦AI | ¥0.3/秒 | ¥0.15/秒 | 闲时: 0:00-8:00 |
| 可灵AI | ¥0.5/秒 | ¥0.25/秒 | 闲时: 23:00-9:00 |

### 单视频成本示例

以5分钟 (300秒) 视频为例：

```
分镜: ¥0
图像: ¥0
TTS: ¥0
视频生成: ¥45 (300秒 × ¥0.15，闲时即梦)
─────────────────
总计: 约¥45-150/视频
```

---

## 九、常见问题

### Q1: Ollama模型下载失败

```powershell
# 设置代理
set HTTPS_PROXY=http://127.0.0.1:7890
ollama pull qwen2.5:14b
```

### Q2: ComfyUI显存不足

```powershell
# 低显存模式启动
python main.py --lowvram

# 或使用更小的模型
# 将SDXL替换为SD1.5模型
```

### Q3: CosyVoice安装失败

建议使用conda环境安装，并确保：
- Python版本为3.10
- PyTorch版本与CUDA版本匹配
- 安装时使用国内镜像源

```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q4: FFmpeg找不到命令

确保FFmpeg已添加到系统PATH：
1. 右键"此电脑" → "属性" → "高级系统设置"
2. "环境变量" → "Path" → 添加FFmpeg的bin目录
3. 重启终端

### Q5: 视频API调用失败

1. 检查API密钥是否正确配置
2. 检查账户余额是否充足
3. 检查网络连接
4. 查看详细错误日志

### Q6: 生成中断如何继续

使用断点续传功能：
```powershell
python -m src.main run --project "项目名" --resume
```

---

## 十、进阶配置

### 自定义LLM提示词

编辑 `config/prompts/` 目录下的文件自定义提示词：
- `storyboard.txt` - 分镜生成提示词
- `character.txt` - 角色提取提示词

### 自定义ComfyUI工作流

可以在ComfyUI中创建自定义工作流，保存为JSON后放入：
- `config/workflows/scene.json` - 场景图生成工作流
- `config/workflows/character.json` - 角色设计工作流

### 使用不同的SDXL模型

1. 下载其他SDXL兼容模型放入 `ComfyUI/models/checkpoints/`
2. 在 `config/settings.yaml` 中指定模型名称

---

## License

MIT License

---

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request
