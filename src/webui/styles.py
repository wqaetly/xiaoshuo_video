"""
WebUI 样式和 JavaScript 代码
"""


def get_custom_css() -> str:
    """获取自定义CSS样式 - 扁平卡片风格"""
    return """
    /* ========== 层次感卡片风格 - 全局变量 ========== */
    :root {
        --bg-primary: #f0f4f8;
        --bg-card: #ffffff;
        --bg-card-elevated: #ffffff;
        --bg-inset: #f8fafc;
        --bg-hover: #f1f5f9;
        --bg-active: #e2e8f0;
        --border-color: #e2e8f0;
        --border-light: #f1f5f9;
        --border-subtle: #eef2f6;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --text-muted: #94a3b8;
        --accent: #3b82f6;
        --accent-light: #eff6ff;
        --accent-hover: #2563eb;
        --success: #10b981;
        --success-light: #ecfdf5;
        --warning: #f59e0b;
        --warning-light: #fffbeb;
        --error: #ef4444;
        --error-light: #fef2f2;
        --radius-xs: 4px;
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --radius-xl: 18px;
        /* 层次感阴影系统 */
        --shadow-xs: 0 1px 2px rgba(0,0,0,0.03);
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -2px rgba(0,0,0,0.03);
        --shadow-card: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
        --shadow-card-hover: 0 8px 16px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.03);
        --shadow-inset: inset 0 1px 2px rgba(0,0,0,0.04);
    }

    /* ========== 全局重置 ========== */
    .gradio-container {
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
        background: var(--bg-primary) !important;
    }

    /* ========== 全局文字 ========== */
    * {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }
    body, .gradio-container, p, span, div {
        font-weight: 400 !important;
        color: var(--text-primary) !important;
    }

    /* 标签文字 */
    label, .label-wrap, .label-wrap span, .gr-input-label, .gr-checkbox-label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        background: transparent !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
    }
    .gr-input-label, .gr-box > label, .gr-form > label,
    span[data-testid="block-label"], [class*="block-label"],
    .label-wrap, .label-wrap > span, div > label, form > label {
        background: transparent !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
    }

    /* 输入框 */
    input, textarea, select, .gr-textbox textarea, .gr-textbox input {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        font-weight: 400 !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-sm) !important;
    }
    input::placeholder, textarea::placeholder {
        color: var(--text-muted) !important;
    }
    input:focus, textarea:focus, select:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-light) !important;
        outline: none !important;
    }

    /* 下拉选项 */
    option, .gr-dropdown li, [data-testid="dropdown"] li {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }

    /* 表格 */
    table, .dataframe, .gr-dataframe { background: var(--bg-card) !important; }
    th { background: var(--bg-hover) !important; color: var(--text-secondary) !important; font-weight: 600 !important; }
    td { background: var(--bg-card) !important; color: var(--text-primary) !important; }

    /* ========== 顶部状态栏 - Column容器 ========== */
    .global-status-bar {
        background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%) !important;
        padding: 12px 20px !important;
        margin: 0 !important;
        gap: 10px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.1) !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 1000 !important;
        border: none !important;
        border-radius: 0 !important;
    }
    /* 状态栏内所有容器透明 */
    .global-status-bar > div,
    .global-status-bar .form,
    .global-status-bar .block {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 第一行：应用标题 */
    .app-title-inline {
        margin: 0 0 4px 0 !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
    }
    .app-title-inline p {
        color: #ffffff !important;
        margin: 0 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }

    /* 第二行：控件Row容器 */
    .status-bar-controls {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 8px !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .status-bar-controls > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* 下拉框 - 占据大部分宽度 */
    .global-project-dropdown {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        box-shadow: none !important;
    }
    .global-project-dropdown label,
    .global-project-dropdown .label-wrap {
        display: none !important;
    }
    .global-project-dropdown > div,
    .global-project-dropdown > div > div,
    .global-project-dropdown .wrap {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* 下拉框输入框样式 */
    .global-project-dropdown input {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        padding: 6px 12px !important;
        color: #ffffff !important;
        box-shadow: none !important;
        height: 34px !important;
        width: 100% !important;
    }
    .global-project-dropdown input::placeholder {
        color: rgba(255, 255, 255, 0.45) !important;
    }
    .global-project-dropdown input:focus {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        outline: none !important;
    }
    /* 下拉箭头 */
    .global-project-dropdown svg {
        color: rgba(255, 255, 255, 0.5) !important;
    }
    /* 下拉列表 */
    .global-project-dropdown ul {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 6px !important;
        box-shadow: 0 6px 20px rgba(0,0,0,0.12) !important;
        margin-top: 4px !important;
        max-height: 260px !important;
        overflow-y: auto !important;
    }
    .global-project-dropdown li {
        color: #374151 !important;
        padding: 8px 12px !important;
        font-size: 13px !important;
    }
    .global-project-dropdown li:hover {
        background: #eff6ff !important;
        color: #2563eb !important;
    }

    /* 刷新按钮 - 透明背景 */
    .status-bar-btn {
        flex: 0 0 auto !important;
        width: 34px !important;
        min-width: 34px !important;
        height: 34px !important;
        background: transparent !important;
        border: none !important;
        color: rgba(255, 255, 255, 0.75) !important;
        padding: 0 !important;
        font-size: 15px !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: color 0.15s ease !important;
    }
    .status-bar-btn:hover {
        color: #ffffff !important;
        background: transparent !important;
    }

    /* ========== 主布局 ========== */
    .main-layout {
        min-height: calc(100vh - 56px) !important;
        gap: 0 !important;
        background: var(--bg-primary) !important;
    }

    /* ========== 侧边栏 - 浮动卡片 ========== */
    .sidebar {
        background: var(--bg-card) !important;
        padding: 16px 10px !important;
        min-height: calc(100vh - 56px) !important;
        max-width: 94px !important;
        min-width: 94px !important;
        border: none !important;
        border-right: none !important;
        box-shadow: var(--shadow-md) !important;
        gap: 6px !important;
        position: relative !important;
        z-index: 10 !important;
    }
    .sidebar > div { gap: 8px !important; padding: 0 !important; }
    .sidebar h3 { display: none !important; }

    /* 导航按钮 - 层次感 */
    .nav-btn {
        width: 100% !important;
        text-align: center !important;
        padding: 16px 8px !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-secondary) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        line-height: 1.4 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .nav-btn:hover {
        background: var(--bg-hover) !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-xs) !important;
        transform: translateX(2px) !important;
    }
    .nav-btn:focus, .nav-btn.selected {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%) !important;
        color: #fff !important;
        outline: none !important;
        box-shadow: var(--shadow-sm), 0 2px 6px rgba(59, 130, 246, 0.3) !important;
    }

    /* ========== 内容区 ========== */
    .content-area {
        background: var(--bg-primary) !important;
        padding: 24px 28px !important;
        min-height: calc(100vh - 56px) !important;
    }
    
    /* ========== 隐藏原生Tab导航 ========== */
    .hidden-tabs > .tab-nav,
    .hidden-tabs > div > .tab-nav,
    .hidden-tabs .tabs > .tab-nav,
    .content-area .tab-nav,
    .content-area > div > .tab-nav,
    div[class*="hidden-tabs"] .tab-nav,
    .hidden-tabs > div[role="tablist"],
    .hidden-tabs [role="tablist"],
    .content-area [role="tablist"],
    div.hidden-tabs > div:first-child,
    .tabs.hidden-tabs > div:first-child {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    /* ========== 卡片式Tab内容区 - 主容器 ========== */
    .hidden-tabs > .tabitem,
    .hidden-tabs .tabitem {
        background: var(--bg-card) !important;
        border-radius: var(--radius-xl) !important;
        padding: 28px !important;
        border: 1px solid var(--border-subtle) !important;
        box-shadow: var(--shadow-md) !important;
        min-height: calc(100vh - 120px) !important;
        transition: box-shadow 0.2s ease !important;
    }

    /* ========== 标题样式 ========== */
    .hidden-tabs h3, .content-area h3 {
        margin: 0 0 24px 0 !important;
        padding: 0 0 12px 0 !important;
        border: none !important;
        border-bottom: 2px solid var(--border-light) !important;
        color: var(--text-primary) !important;
        font-size: 17px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }

    /* ========== 内嵌卡片/分组 - 层次感 ========== */
    .hidden-tabs .group, .content-area .group, .group, .gr-group {
        background: var(--bg-inset) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: var(--radius-md) !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
        box-shadow: var(--shadow-inset) !important;
        transition: all 0.2s ease !important;
    }

    /* 内嵌卡片悬浮效果 */
    .hidden-tabs .group:hover, .content-area .group:hover {
        background: var(--bg-hover) !important;
        box-shadow: var(--shadow-xs) !important;
    }

    /* 二级嵌套分组 */
    .group .group, .gr-group .gr-group {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--shadow-sm) !important;
        padding: 16px !important;
    }

    /* 全局消除黑线 - 覆盖 Gradio 默认深色边框 */
    .gr-box, .gr-form, .gr-panel, .gr-block, .block, .form, .panel,
    .gr-input, .gr-textbox, .gr-dropdown, .gr-number, .gr-slider,
    .gr-checkbox, .gr-radio, .gr-file, .gr-gallery, .gr-video, .gr-audio,
    .gr-image, .gr-json, .gr-dataframe, .gr-markdown, .gr-accordion,
    .tabitem, .tab-content, .tabs, [class*="block"], [class*="container"],
    div[data-testid], form, fieldset {
        border-color: var(--border-color) !important;
    }

    /* 确保所有嵌套容器边框统一 */
    .gr-box > div, .gr-form > div, .gr-panel > div, .block > div,
    .form > div, .panel > div, .tabitem > div, .group > div {
        border-color: var(--border-color) !important;
    }

    /* 消除 Row 和 Column 之间的黑线 */
    .gr-row, .gr-column, .row, .column, .svelte-1gfkn6j,
    [class*="row"], [class*="column"], [class*="Row"], [class*="Column"] {
        border: none !important;
        box-shadow: none !important;
    }

    /* 输入组件容器边框统一 */
    .wrap, .container, .input-container, .textbox-container,
    .dropdown-container, .number-container, .slider-container {
        border-color: var(--border-color) !important;
    }

    .accordion {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    .accordion:hover {
        box-shadow: var(--shadow-md) !important;
    }
    .accordion > .label-wrap {
        background: linear-gradient(180deg, var(--bg-hover) 0%, var(--bg-inset) 100%) !important;
        padding: 14px 18px !important;
        border-bottom: 1px solid var(--border-light) !important;
        cursor: pointer !important;
        transition: background 0.15s ease !important;
    }
    .accordion > .label-wrap:hover {
        background: var(--bg-hover) !important;
    }
    .accordion > .label-wrap span {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }
    .accordion > .content {
        padding: 16px 18px !important;
        background: var(--bg-card) !important;
    }

    /* ========== 按钮样式 - 层次感 ========== */
    button, .gr-button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 10px 18px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-xs) !important;
        border: 1px solid transparent !important;
    }
    button.primary, .gr-button.primary {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%) !important;
        color: #fff !important;
        box-shadow: var(--shadow-sm), 0 2px 4px rgba(59, 130, 246, 0.2) !important;
    }
    button.primary:hover, .gr-button.primary:hover {
        background: linear-gradient(135deg, var(--accent-hover) 0%, #1d4ed8 100%) !important;
        box-shadow: var(--shadow-md), 0 4px 8px rgba(59, 130, 246, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    button.secondary, .gr-button.secondary {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-secondary) !important;
        box-shadow: var(--shadow-xs) !important;
    }
    button.secondary:hover, .gr-button.secondary:hover {
        background: var(--bg-hover) !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-sm) !important;
        transform: translateY(-1px) !important;
    }
    button.stop, .gr-button.stop {
        background: linear-gradient(135deg, var(--error) 0%, #dc2626 100%) !important;
        color: #fff !important;
        box-shadow: var(--shadow-sm), 0 2px 4px rgba(239, 68, 68, 0.2) !important;
    }
    button.stop:hover, .gr-button.stop:hover {
        box-shadow: var(--shadow-md), 0 4px 8px rgba(239, 68, 68, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    button:active, .gr-button:active {
        transform: translateY(0) !important;
    }

    /* ========== 输入框样式 - 内嵌感 ========== */
    input, textarea, select, .gr-input, .gr-textarea {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-sm) !important;
        box-shadow: var(--shadow-inset) !important;
        font-size: 13px !important;
        padding: 11px 14px !important;
        background: var(--bg-inset) !important;
        transition: all 0.2s ease !important;
    }
    input:hover, textarea:hover, select:hover {
        background: var(--bg-card) !important;
        border-color: var(--border-color) !important;
    }
    input:focus, textarea:focus, select:focus {
        background: var(--bg-card) !important;
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-light), var(--shadow-sm) !important;
        outline: none !important;
    }

    /* ========== 下拉框 ========== */
    .gr-dropdown {
        border-radius: var(--radius-sm) !important;
    }
    .gr-dropdown .wrap {
        background: var(--bg-inset) !important;
        box-shadow: var(--shadow-inset) !important;
    }
    .gr-dropdown:hover .wrap {
        background: var(--bg-card) !important;
    }

    /* ========== 表格样式 - 卡片化 ========== */
    .dataframe, .gr-dataframe {
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
        background: var(--bg-card) !important;
    }
    .dataframe thead th {
        background: var(--bg-inset) !important;
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        padding: 14px 16px !important;
        border-bottom: 1px solid var(--border-color) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.02em !important;
    }
    .dataframe tbody td {
        padding: 14px 16px !important;
        font-size: 13px !important;
        border-bottom: 1px solid var(--border-light) !important;
    }
    .dataframe tbody tr {
        transition: background 0.15s ease !important;
    }
    .dataframe tbody tr:hover {
        background: var(--bg-hover) !important;
    }
    .dataframe tbody tr:last-child td {
        border-bottom: none !important;
    }
    
    /* ========== JSON显示 - 代码风格 ========== */
    .json, .gr-json {
        background: var(--bg-inset) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px !important;
        box-shadow: var(--shadow-inset) !important;
    }
    .json pre, .gr-json pre {
        background: transparent !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', 'Fira Code', 'Monaco', 'Consolas', monospace !important;
        font-size: 12px !important;
        line-height: 1.6 !important;
    }

    /* ========== 图片/视频/音频组件 - 卡片化 ========== */
    .gr-image, .gr-video, .gr-audio, .gr-gallery {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s ease !important;
    }
    .gr-image:hover, .gr-video:hover, .gr-audio:hover, .gr-gallery:hover {
        box-shadow: var(--shadow-md) !important;
    }
    .gr-image img, .gr-video video {
        border-radius: var(--radius-md) !important;
    }

    /* Gallery 缩略图 */
    .gr-gallery .thumbnail {
        border-radius: var(--radius-sm) !important;
        border: 2px solid transparent !important;
        transition: all 0.15s ease !important;
    }
    .gr-gallery .thumbnail:hover {
        border-color: var(--accent) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    .gr-gallery .thumbnail.selected {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-light) !important;
    }

    /* ========== 滑块组件 ========== */
    .gr-slider {
        padding: 8px 0 !important;
    }
    .gr-slider input[type="range"] {
        background: var(--bg-hover) !important;
        border-radius: 4px !important;
        height: 6px !important;
    }
    .gr-slider input[type="range"]::-webkit-slider-thumb {
        background: var(--accent) !important;
        box-shadow: var(--shadow-sm) !important;
        width: 16px !important;
        height: 16px !important;
        border-radius: 50% !important;
        border: 2px solid var(--bg-card) !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }
    .gr-slider input[type="range"]::-webkit-slider-thumb:hover {
        transform: scale(1.15) !important;
        box-shadow: var(--shadow-md), 0 0 0 4px var(--accent-light) !important;
    }

    /* ========== 文件上传组件 ========== */
    .gr-file, .upload-button {
        background: var(--bg-inset) !important;
        border: 2px dashed var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        padding: 24px !important;
        transition: all 0.2s ease !important;
    }
    .gr-file:hover, .upload-button:hover {
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
    }

    /* ========== Gradio主题覆盖 ========== */
    .dark, [data-theme="dark"], :root {
        --body-background-fill: var(--bg-primary) !important;
        --block-background-fill: var(--bg-card) !important;
        --input-background-fill: var(--bg-card) !important;
        --color-background-primary: var(--bg-card) !important;
        --color-background-secondary: var(--bg-primary) !important;
        --background-fill-primary: var(--bg-card) !important;
        --background-fill-secondary: var(--bg-primary) !important;
        --neutral-50: var(--bg-primary) !important;
        --neutral-100: var(--bg-hover) !important;
        --neutral-200: var(--border-color) !important;
        --neutral-800: var(--text-primary) !important;
        --neutral-900: #1a202c !important;
        --body-text-color: var(--text-primary) !important;
        --block-label-text-color: var(--text-secondary) !important;
        --block-title-text-color: var(--text-primary) !important;
        --input-text-color: var(--text-primary) !important;
        --checkbox-label-text-color: var(--text-primary) !important;
        --block-label-background-fill: transparent !important;
        --block-label-border-color: transparent !important;
        --input-border-color: var(--border-color) !important;
        /* 修复黑线问题 - 统一边框颜色 */
        --border-color-primary: var(--border-color) !important;
        --border-color-accent: var(--border-color) !important;
        --block-border-color: var(--border-color) !important;
        --panel-border-color: var(--border-color) !important;
        --table-border-color: var(--border-color) !important;
        --input-border-color-focus: var(--accent) !important;
        --color-border-primary: var(--border-color) !important;
        --color-border-secondary: var(--border-light) !important;
    }
    /* 全局背景 */
    body, .gradio-container, .main, .contain, .wrap, #root, main {
        background: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }
    /* 块级元素 */
    .gr-box, .gr-form, .gr-panel, .gr-block, .block, .form, .panel {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-color) !important;
    }
    /* 标签 */
    .gr-input-label, .gr-checkbox-label, label, .label-wrap, .label-wrap span,
    span[data-testid="block-label"], .block-label, .input-label {
        color: var(--text-secondary) !important;
        background: transparent !important;
    }
    label span, .label-wrap span, .gr-input-label span {
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    /* Checkbox 和 Radio */
    .gr-check-radio, .gr-checkbox, .checkbox, .radio {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    /* Group 组件 */
    .gr-group, .group {
        background: var(--bg-hover) !important;
        border-color: var(--border-color) !important;
    }
    /* 下拉菜单 */
    .gr-dropdown, .gr-dropdown .wrap, .gr-dropdown ul,
    [data-testid="dropdown"], [data-testid="dropdown"] ul,
    .dropdown, select {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-color) !important;
    }
    .gr-dropdown li:hover, [data-testid="dropdown"] li:hover {
        background: var(--bg-hover) !important;
    }
    /* 文本区域和输入框 */
    textarea, .gr-text-input, input[type="text"], input[type="number"], input[type="password"],
    .textbox {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-color) !important;
    }
    /* Accordion */
    .gr-accordion, .accordion {
        background: var(--bg-card) !important;
        border-color: var(--border-color) !important;
    }
    .gr-accordion > .label-wrap, .accordion > .label-wrap {
        background: var(--bg-hover) !important;
        color: var(--text-primary) !important;
    }
    .gr-accordion .icon, .accordion .icon {
        color: var(--text-muted) !important;
    }
    /* 进度条 - 扁平化 */
    .gr-progress-bar, .progress-bar {
        background: var(--border-color) !important;
        border-radius: var(--radius-sm) !important;
    }
    .gr-progress-bar > div, .progress-bar > div {
        background: var(--accent) !important;
        border-radius: var(--radius-sm) !important;
    }
    /* Dataframe 表格 */
    .gr-dataframe, .dataframe, table, .table-wrap {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    .gr-dataframe th, .dataframe th, table th, thead th {
        background: var(--bg-hover) !important;
        color: var(--text-secondary) !important;
    }
    .gr-dataframe td, .dataframe td, table td, tbody td {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    .gr-dataframe tr:hover td, .dataframe tr:hover td, table tr:hover td {
        background: var(--bg-hover) !important;
    }
    /* Slider 滑块 */
    .gr-slider, .slider, input[type="range"] {
        background: transparent !important;
    }
    .gr-slider .wrap, .slider .wrap {
        background: var(--bg-card) !important;
    }
    /* Number 输入 */
    .gr-number, .gr-number input {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }
    /* Radio 和 Checkbox 组 */
    .gr-radio, .gr-checkbox-group, .radio-group, .checkbox-group {
        background: var(--bg-card) !important;
    }
    .gr-radio label, .gr-checkbox-group label {
        color: var(--text-primary) !important;
    }
    /* File 上传 */
    .gr-file, .gr-upload, .upload-container {
        background: var(--bg-hover) !important;
        border: 2px dashed var(--border-color) !important;
        border-radius: var(--radius-md) !important;
    }
    .gr-file:hover, .gr-upload:hover {
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
    }
    /* Gallery */
    .gr-gallery, .gallery {
        background: var(--bg-card) !important;
    }
    /* Video 和 Image */
    .gr-video, .gr-image, .video-container, .image-container {
        background: var(--bg-hover) !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border-color) !important;
    }
    /* Markdown */
    .gr-markdown, .markdown, .prose {
        color: var(--text-primary) !important;
    }
    .gr-markdown h1, .gr-markdown h2, .gr-markdown h3,
    .markdown h1, .markdown h2, .markdown h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    /* 状态徽章 */
    .status-badge {
        background: var(--bg-hover) !important;
        color: var(--text-secondary) !important;
        padding: 4px 10px !important;
        border-radius: var(--radius-sm) !important;
        font-size: 12px !important;
    }
    /* 按钮文字 */
    button.primary, .gr-button.primary {
        color: #ffffff !important;
    }
    button.secondary, .gr-button.secondary {
        color: var(--text-secondary) !important;
        background: var(--bg-card) !important;
    }
    button.stop, .gr-button.stop {
        color: #ffffff !important;
    }

    /* ========== 提示文本 ========== */
    .hint-text p, .hint-text span, .hint-text {
        color: var(--text-muted) !important;
        font-size: 12px !important;
        font-style: normal !important;
        font-weight: 400 !important;
        margin: 4px 0 8px 0 !important;
    }
    /* 项目信息卡片 - 扁平化 */
    .project-info-card {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow-card) !important;
    }
    /* 进度统计卡片 */
    .progress-stats {
        background: var(--bg-hover) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px !important;
    }

    /* ========== 分镜页面布局优化 ========== */
    #sortable-scene-list {
        overflow: hidden !important;
    }
    #sortable-scene-list > div {
        overflow: hidden !important;
    }

    /* ========== 场景列表 - 扁平卡片风 ========== */
    .sortable-scene-container {
        display: flex;
        flex-direction: column;
        gap: 6px;
        height: 420px;
        min-height: 300px;
        max-height: calc(100vh - 340px);
        overflow-y: auto;
        overflow-x: hidden;
        padding: 10px;
        background: var(--bg-hover);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
    }
    .sortable-scene-container::-webkit-scrollbar {
        width: 5px;
    }
    .sortable-scene-container::-webkit-scrollbar-track {
        background: transparent;
    }
    .sortable-scene-container::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 3px;
    }
    .sortable-scene-container::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    .scene-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        cursor: pointer;
        transition: all 0.15s ease;
        flex-shrink: 0;
        min-width: 0;
    }
    .scene-item:hover {
        border-color: var(--accent);
        background: var(--accent-light);
    }
    .scene-item.selected {
        border-color: var(--accent);
        background: var(--accent-light);
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .scene-item.dragging {
        opacity: 0.6;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .scene-drag-handle {
        color: var(--text-muted);
        font-size: 12px;
        cursor: grab;
        flex-shrink: 0;
    }
    .scene-index {
        min-width: 24px;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-hover);
        border-radius: var(--radius-sm);
        font-size: 10px;
        font-weight: 600;
        color: var(--text-secondary);
        flex-shrink: 0;
    }
    .scene-thumb {
        width: 48px;
        height: 32px;
        background: var(--bg-hover);
        border-radius: var(--radius-sm);
        flex-shrink: 0;
        background-size: cover;
        background-position: center;
        border: 1px solid var(--border-light);
    }
    .scene-info {
        flex: 1;
        min-width: 0;
        overflow: hidden;
    }
    .scene-id {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .scene-desc {
        font-size: 11px;
        color: var(--text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 2px;
        max-width: 100%;
    }
    .scene-meta {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 3px;
        flex-shrink: 0;
    }
    .scene-duration {
        font-size: 10px;
        color: var(--text-secondary);
        background: var(--bg-hover);
        padding: 2px 6px;
        border-radius: var(--radius-sm);
        white-space: nowrap;
    }
    .scene-status {
        font-size: 11px;
        flex-shrink: 0;
    }
    .scene-list-empty {
        padding: 40px 16px;
        text-align: center;
        color: var(--text-muted);
        font-size: 13px;
    }
    .drag-hint {
        margin-top: 8px;
        font-size: 11px;
        color: var(--text-muted);
        text-align: center;
    }
    mark { background: var(--warning); color: #fff; padding: 1px 4px; border-radius: 3px; }

    /* ========== 分镜筛选区域 ========== */
    #filter-result-info {
        margin-top: 8px !important;
    }
    #filter-result-info p {
        font-size: 12px !important;
        color: var(--text-secondary) !important;
    }

    /* ========== 场景编辑器区域 ========== */
    #scene-selector-dropdown {
        margin-bottom: 12px !important;
    }
    #scene-selector-dropdown input {
        font-weight: 600 !important;
        color: var(--accent) !important;
    }

    /* 分镜页面两栏布局优化 */
    .gr-row > .gr-column {
        overflow: hidden !important;
    }

    /* 场景预览图片 */
    .scene-preview-container {
        max-height: 280px !important;
        overflow: hidden !important;
        border-radius: var(--radius-md) !important;
    }

    /* ========== 日志区域 ========== */
    #realtime-log textarea {
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
        font-size: 11px !important;
        background: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
        padding: 14px !important;
    }

    /* ========== 滑块 ========== */
    .gr-slider input[type="range"] {
        accent-color: var(--accent) !important;
    }

    /* ========== 复选框/单选框 ========== */
    .gr-checkbox input, .gr-radio input {
        accent-color: var(--accent) !important;
    }

    /* ========== 标签页导航 ========== */
    .gr-tab-nav button {
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
        font-weight: 500 !important;
        background: var(--bg-hover) !important;
        border: none !important;
        color: var(--text-secondary) !important;
    }
    .gr-tab-nav button.selected {
        background: var(--bg-card) !important;
        color: var(--accent) !important;
    }

    /* ========== 黑线修复 - 综合覆盖 ========== */
    /* 消除所有深色边框，统一为浅色边框 */
    * {
        --tw-border-opacity: 1 !important;
    }

    /* Gradio Svelte 组件边框修复 */
    [class*="svelte-"] {
        border-color: var(--border-color) !important;
    }

    /* 输入组件外层容器 */
    .gr-form > div, .gr-box > div, .gr-panel > div,
    .wrap > div, .container > div, .block > div {
        border-color: var(--border-color) !important;
    }

    /* 表单元素分隔线 */
    hr, .divider, .separator {
        border-color: var(--border-light) !important;
        background: var(--border-light) !important;
    }

    /* 内联块元素 */
    .inline-block, .inline-flex {
        border-color: var(--border-color) !important;
    }

    /* Gallery 和 File 组件 */
    .gr-gallery .thumbnail, .gr-file .file-preview,
    .gallery .thumbnail, .upload-container .file-preview {
        border-color: var(--border-color) !important;
    }

    /* Dataframe 表格边框 */
    .gr-dataframe table, .dataframe table,
    .gr-dataframe th, .dataframe th,
    .gr-dataframe td, .dataframe td,
    table, th, td {
        border-color: var(--border-color) !important;
    }

    /* JSON 显示区域 */
    .gr-json, .json, pre, code {
        border-color: var(--border-color) !important;
    }

    /* 视频和图片容器 */
    .gr-video, .gr-image, .gr-audio,
    video, img.preview, .video-container, .image-container, .audio-container {
        border-color: var(--border-color) !important;
    }

    /* 进度条容器 */
    .gr-progress, .progress, .progress-bar {
        border-color: var(--border-color) !important;
    }

    /* 确保 fieldset 和 legend 无黑线 */
    fieldset {
        border-color: var(--border-color) !important;
    }
    legend {
        background: var(--bg-card) !important;
    }

    /* ========== 响应式布局 ========== */
    @media (max-width: 1200px) {
        .sortable-scene-container {
            height: 320px !important;
            max-height: 320px !important;
        }
    }
    @media (max-width: 1024px) {
        .main-layout { flex-direction: column !important; }
        .sidebar {
            max-width: 100% !important;
            min-width: 100% !important;
            min-height: auto !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            padding: 10px !important;
        }
        .sidebar > div {
            flex-direction: row !important;
            gap: 8px !important;
        }
        .nav-btn {
            padding: 10px 16px !important;
            white-space: nowrap !important;
        }
        .content-area {
            padding: 16px !important;
        }
        .sortable-scene-container {
            height: 280px !important;
            max-height: 280px !important;
        }
    }
    """


def get_drag_sort_js() -> str:
    """获取拖拽排序的JavaScript代码"""
    return """
    (function() {
        if (window._dragSortInitialized) return;
        window._dragSortInitialized = true;
        
        function initDragSort() {
            const container = document.getElementById('scene-container');
            if (!container || container.hasAttribute('data-drag-init')) return;
            container.setAttribute('data-drag-init', 'true');
            let draggedItem = null, draggedIndex = -1;

            container.querySelectorAll('.scene-item').forEach((item, index) => {
                item.setAttribute('data-index', index);
                item.addEventListener('dragstart', (e) => {
                    draggedItem = item; draggedIndex = index;
                    item.classList.add('dragging');
                    e.dataTransfer.effectAllowed = 'move';
                });
                item.addEventListener('dragend', () => {
                    item.classList.remove('dragging');
                    container.querySelectorAll('.scene-item').forEach(i => i.classList.remove('drag-over'));
                    updateOrderState();
                });
                item.addEventListener('dragover', (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
                item.addEventListener('dragenter', (e) => { e.preventDefault(); if (item !== draggedItem) item.classList.add('drag-over'); });
                item.addEventListener('dragleave', () => item.classList.remove('drag-over'));
                item.addEventListener('drop', (e) => {
                    e.preventDefault(); item.classList.remove('drag-over');
                    if (draggedItem && item !== draggedItem) {
                        const allItems = [...container.querySelectorAll('.scene-item')];
                        const dropIndex = allItems.indexOf(item);
                        if (draggedIndex < dropIndex) item.parentNode.insertBefore(draggedItem, item.nextSibling);
                        else item.parentNode.insertBefore(draggedItem, item);
                    }
                });
                item.addEventListener('click', (e) => {
                    if (e.target.classList.contains('scene-drag-handle')) return;
                    container.querySelectorAll('.scene-item').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                    
                    // 同步更新场景选择下拉框
                    const sceneId = item.getAttribute('data-scene-id');
                    if (sceneId) {
                        // 通过 elem_id 精确定位下拉框
                        const selectorContainer = document.getElementById('scene-selector-dropdown');
                        if (selectorContainer) {
                            const input = selectorContainer.querySelector('input');
                            if (input) {
                                input.value = sceneId;
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                input.dispatchEvent(new Event('change', { bubbles: true }));
                                // 触发 blur 以确保 Gradio 捕获变化
                                input.dispatchEvent(new Event('blur', { bubbles: true }));
                            }
                        }
                    }
                });
            });

            function updateOrderState() {
                const items = container.querySelectorAll('.scene-item');
                const order = [...items].map(item => item.getAttribute('data-scene-id'));
                const stateInput = document.getElementById('scene-order-state');
                if (stateInput) {
                    const textarea = stateInput.querySelector('textarea');
                    if (textarea) { textarea.value = order.join(','); textarea.dispatchEvent(new Event('input', { bubbles: true })); }
                }
                items.forEach((item, idx) => { const el = item.querySelector('.scene-index'); if (el) el.textContent = idx; });
            }
        }

        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDragSort);
        else setTimeout(initDragSort, 100);

        let debounceTimer = null;
        const observer = new MutationObserver(() => {
            if (debounceTimer) return;
            debounceTimer = setTimeout(() => {
                debounceTimer = null;
                const container = document.getElementById('scene-container');
                if (container && !container.hasAttribute('data-drag-init')) initDragSort();
            }, 200);
        });
        const targetNode = document.getElementById('sortable-scene-list');
        if (targetNode) observer.observe(targetNode, { childList: true, subtree: true });
    })();
    """
