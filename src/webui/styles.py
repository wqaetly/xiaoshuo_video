"""
WebUI 样式和 JavaScript 代码
"""


def get_custom_css() -> str:
    """获取自定义CSS样式 - 现代简洁设计"""
    return """
    /* ========== 全局重置 ========== */
    .gradio-container {
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
        background: #f8fafc !important;
    }
    
    /* ========== 全局文字增强 ========== */
    * {
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }
    /* 只对浅色背景元素设置深色文字 */
    body, .gradio-container, p, span, div {
        font-weight: 500 !important;
    }
    /* 标签文字加粗 - 强制浅色背景 */
    label, .label-wrap, .label-wrap span, .gr-input-label, .gr-checkbox-label {
        color: #334155 !important;
        font-weight: 600 !important;
        background: transparent !important;
    }
    /* Gradio 标签容器 - 关键修复 */
    .gr-input-label, .gr-box > label, .gr-form > label,
    span[data-testid="block-label"], [class*="block-label"],
    .label-wrap, .label-wrap > span, 
    div > label, form > label,
    .svelte-1gfkn6j, .svelte-s1r2yt {
        background: transparent !important;
        background-color: transparent !important;
        color: #334155 !important;
        font-weight: 600 !important;
    }
    /* 标签父容器也要透明 */
    .gr-input-label span, label span, .label-wrap span {
        background: transparent !important;
        background-color: transparent !important;
    }
    /* 输入框 - 确保白色背景+深色文字 */
    input, textarea, select, .gr-textbox textarea, .gr-textbox input {
        background: #ffffff !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }
    /* 占位符文字 */
    input::placeholder, textarea::placeholder {
        color: #94a3b8 !important;
        font-weight: 400 !important;
    }
    /* 下拉选项 - 确保白色背景 */
    option, .gr-dropdown li, [data-testid="dropdown"] li {
        background: #ffffff !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }
    /* 表格 - 确保白色背景 */
    table, .dataframe, .gr-dataframe {
        background: #ffffff !important;
    }
    th {
        background: #f1f5f9 !important;
        color: #334155 !important;
        font-weight: 700 !important;
    }
    td {
        background: #ffffff !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }
    
    /* ========== 标题栏 ========== */
    .app-title {
        padding: 12px 20px !important;
        margin: 0 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25) !important;
    }
    .app-title h1 {
        color: #fff !important;
        margin: 0 !important;
        font-size: 18px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
    }
    
    /* ========== 全局状态栏 ========== */
    .global-status-bar {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        padding: 10px 20px !important;
        margin: 0 !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 16px !important;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3) !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 1000 !important;
        min-height: 48px !important;
        border: none !important;
    }
    /* 状态栏内所有子元素重置 */
    .global-status-bar > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .app-title-inline {
        flex: 0 0 auto !important;
        margin: 0 !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
    }
    .app-title-inline p {
        color: #fff !important;
        margin: 0 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        white-space: nowrap !important;
    }

    .global-project-dropdown {
        flex: 1 !important;
        max-width: none !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .global-project-dropdown > label,
    .global-project-dropdown .label-wrap {
        display: none !important;
    }
    .global-project-dropdown > div,
    .global-project-dropdown .wrap,
    .global-project-dropdown .container,
    .global-project-dropdown [class*="wrap"],
    .global-project-dropdown [class*="container"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .global-project-dropdown input,
    .global-project-dropdown .svelte-1gfkn6j {
        background: rgba(255, 255, 255, 0.95) !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        padding: 8px 14px !important;
        color: #1e293b !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        height: 38px !important;
    }
    .global-project-dropdown input::placeholder {
        color: #64748b !important;
    }
    .global-project-dropdown input:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    .status-bar-btn {
        flex: 0 0 auto !important;
        background: rgba(255, 255, 255, 0.2) !important;
        border: none !important;
        color: #fff !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        font-size: 16px !important;
        min-width: 40px !important;
        height: 38px !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .status-bar-btn:hover {
        background: rgba(255, 255, 255, 0.35) !important;
        transform: scale(1.05) !important;
    }
    
    /* ========== 主布局 ========== */
    .main-layout {
        min-height: calc(100vh - 60px) !important;
        gap: 0 !important;
        background: #f8fafc !important;
    }
    
    /* ========== 侧边栏 ========== */
    .sidebar {
        background: #f1f5f9 !important;
        padding: 8px 0 !important;
        min-height: calc(100vh - 60px) !important;
        max-width: 100px !important;
        min-width: 100px !important;
        border: none !important;
        border-right: 1px solid #e2e8f0 !important;
        gap: 4px !important;
    }
    .sidebar > div { gap: 4px !important; padding: 0 6px !important; }
    .sidebar h3 { display: none !important; }
    
    /* 导航按钮 */
    .nav-btn {
        width: 100% !important;
        text-align: center !important;
        padding: 12px 6px !important;
        margin: 2px 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        color: #64748b !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        line-height: 1.3 !important;
        transition: all 0.2s ease !important;
    }
    .nav-btn:hover {
        background: #e2e8f0 !important;
        color: #1e293b !important;
    }
    .nav-btn:focus, .nav-btn.selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: #fff !important;
        outline: none !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* ========== 内容区 ========== */
    .content-area {
        background: #f8fafc !important;
        padding: 16px 20px !important;
        min-height: calc(100vh - 60px) !important;
    }
    
    /* ========== 隐藏原生Tab导航 ========== */
    .hidden-tabs > .tab-nav,
    .hidden-tabs > div > .tab-nav,
    .hidden-tabs .tabs > .tab-nav,
    .content-area .tab-nav,
    .content-area > div > .tab-nav,
    div[class*="hidden-tabs"] .tab-nav,
    .tabitem > .tabs > .tab-nav,
    /* Gradio 4.x/5.x 新选择器 */
    .hidden-tabs > div[role="tablist"],
    .hidden-tabs [role="tablist"],
    .content-area [role="tablist"],
    .hidden-tabs > div:first-child:has(button[role="tab"]),
    .content-area > div > div:first-child:has(button[role="tab"]),
    div.hidden-tabs > div:first-child,
    .tabs.hidden-tabs > div:first-child { 
        display: none !important; 
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    .hidden-tabs > .tabitem,
    .hidden-tabs .tabitem {
        background: #fff !important;
        border-radius: 12px !important;
        padding: 20px !important;
        border: none !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.03) !important;
        min-height: calc(100vh - 100px) !important;
    }
    
    /* ========== 标题样式 ========== */
    .hidden-tabs h3, .content-area h3 {
        margin: 0 0 16px 0 !important;
        padding: 0 0 10px 0 !important;
        border-bottom: 2px solid #e2e8f0 !important;
        color: #1e293b !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    
    /* ========== 卡片/分组 ========== */
    .hidden-tabs .group, .hidden-tabs .accordion, .content-area .group {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 14px !important;
        margin-bottom: 12px !important;
        box-shadow: none !important;
    }
    .accordion > .label-wrap {
        background: transparent !important;
        padding: 8px 0 !important;
    }
    
    /* ========== 按钮样式 ========== */
    button, .gr-button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    button.primary, .gr-button.primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: #fff !important;
    }
    button.primary:hover, .gr-button.primary:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
    }
    button.secondary, .gr-button.secondary {
        background: #fff !important;
        border: 1px solid #e2e8f0 !important;
        color: #475569 !important;
    }
    button.secondary:hover, .gr-button.secondary:hover {
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
    }
    button.stop, .gr-button.stop {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        border: none !important;
        color: #fff !important;
    }
    
    /* ========== 输入框样式 ========== */
    input, textarea, select, .gr-input, .gr-textarea {
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
        font-size: 13px !important;
        padding: 10px 12px !important;
        background: #fff !important;
        transition: all 0.2s ease !important;
    }
    input:focus, textarea:focus, select:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        outline: none !important;
    }
    
    /* ========== 下拉框 ========== */
    .gr-dropdown {
        border-radius: 8px !important;
    }
    
    /* ========== 表格样式 ========== */
    .dataframe, .gr-dataframe {
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .dataframe thead th {
        background: #f1f5f9 !important;
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        padding: 10px 12px !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    .dataframe tbody td {
        padding: 10px 12px !important;
        font-size: 13px !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    .dataframe tbody tr:hover {
        background: #f8fafc !important;
    }
    
    /* ========== JSON显示 ========== */
    .json, .gr-json {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 12px !important;
    }
    .json pre, .gr-json pre {
        background: #f8fafc !important;
        color: #1e293b !important;
    }

    /* ========== 强制浅色背景 ========== */
    .dark, [data-theme="dark"], :root {
        --body-background-fill: #f8fafc !important;
        --block-background-fill: #ffffff !important;
        --input-background-fill: #ffffff !important;
        --color-background-primary: #ffffff !important;
        --color-background-secondary: #f8fafc !important;
        --background-fill-primary: #ffffff !important;
        --background-fill-secondary: #f8fafc !important;
        --neutral-50: #f8fafc !important;
        --neutral-100: #f1f5f9 !important;
        --neutral-200: #e2e8f0 !important;
        --neutral-800: #1e293b !important;
        --neutral-900: #0f172a !important;
        --body-text-color: #1e293b !important;
        --block-label-text-color: #334155 !important;
        --block-title-text-color: #1e293b !important;
        --input-text-color: #1e293b !important;
        --checkbox-label-text-color: #1e293b !important;
        --block-label-background-fill: transparent !important;
        --block-label-border-color: transparent !important;
        --input-border-color: #e2e8f0 !important;
    }
    /* 全局背景覆盖 */
    body, .gradio-container, .main, .contain, .wrap, #root, main {
        background: #f8fafc !important;
        color: #1e293b !important;
    }
    /* 所有块级元素 */
    .gr-box, .gr-form, .gr-panel, .gr-block, .block, 
    .form, .panel, [class*="block"], [class*="panel"] {
        background: #ffffff !important;
        color: #1e293b !important;
        border-color: #e2e8f0 !important;
    }
    /* 标签 - 关键：强制透明背景 */
    .gr-input-label, .gr-checkbox-label, label, .label-wrap, .label-wrap span,
    [class*="label"], span.svelte-1gfkn6j, span[data-testid="block-label"],
    .block-label, .input-label {
        color: #334155 !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    /* 标签内的 span */
    label span, .label-wrap span, .gr-input-label span {
        background: transparent !important;
        background-color: transparent !important;
        color: #334155 !important;
    }
    /* Checkbox 和 Radio */
    .gr-check-radio, .gr-checkbox, .checkbox, .radio,
    [class*="checkbox"], [class*="radio"] {
        background: #ffffff !important;
        color: #1e293b !important;
    }
    /* Group 组件 */
    .gr-group, .group, div[class*="group"], .svelte-1kyws56 {
        background: #f8fafc !important;
        border-color: #e2e8f0 !important;
    }
    /* 下拉菜单 */
    .gr-dropdown, .gr-dropdown .wrap, .gr-dropdown ul, 
    [data-testid="dropdown"], [data-testid="dropdown"] ul,
    .dropdown, select, [class*="dropdown"] {
        background: #ffffff !important;
        color: #1e293b !important;
        border-color: #e2e8f0 !important;
    }
    .gr-dropdown li:hover, [data-testid="dropdown"] li:hover {
        background: #f1f5f9 !important;
    }
    /* 文本区域和输入框 */
    textarea, .gr-text-input, input[type="text"], input[type="number"], input[type="password"],
    .textbox, [class*="textbox"], .svelte-1f354aw {
        background: #ffffff !important;
        color: #1e293b !important;
        border-color: #e2e8f0 !important;
    }
    /* Accordion */
    .gr-accordion, .accordion, div[class*="accordion"], .svelte-kzcjhc {
        background: #ffffff !important;
        border-color: #e2e8f0 !important;
    }
    .gr-accordion > .label-wrap, .accordion > .label-wrap,
    .svelte-kzcjhc > .label-wrap {
        background: #f8fafc !important;
        color: #1e293b !important;
    }
    .gr-accordion .icon, .accordion .icon {
        color: #64748b !important;
    }
    /* 进度条 */
    .gr-progress-bar, .progress-bar, [class*="progress"] {
        background: #e2e8f0 !important;
    }
    .gr-progress-bar > div, .progress-bar > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    }
    /* Dataframe 表格 */
    .gr-dataframe, .dataframe, table, .table-wrap, .svelte-1byz9vf {
        background: #ffffff !important;
        color: #1e293b !important;
    }
    .gr-dataframe th, .dataframe th, table th, thead th {
        background: #f1f5f9 !important;
        color: #334155 !important;
    }
    .gr-dataframe td, .dataframe td, table td, tbody td {
        background: #ffffff !important;
        color: #1e293b !important;
    }
    .gr-dataframe tr:hover td, .dataframe tr:hover td, table tr:hover td {
        background: #f8fafc !important;
    }
    /* Slider 滑块 */
    .gr-slider, .slider, input[type="range"], [class*="slider"] {
        background: transparent !important;
    }
    .gr-slider .wrap, .slider .wrap {
        background: #ffffff !important;
    }
    /* Number 输入 */
    .gr-number, .gr-number input, [class*="number"] input {
        background: #ffffff !important;
        color: #1e293b !important;
    }
    /* Radio 和 Checkbox 组 */
    .gr-radio, .gr-checkbox-group, .radio-group, .checkbox-group,
    [class*="radio-group"], [class*="checkbox-group"] {
        background: #ffffff !important;
    }
    .gr-radio label, .gr-checkbox-group label {
        color: #1e293b !important;
    }
    /* File 上传 */
    .gr-file, .gr-upload, .upload-container, [data-testid="file"],
    [class*="upload"], [class*="file"] {
        background: #f8fafc !important;
        border-color: #e2e8f0 !important;
    }
    /* Gallery */
    .gr-gallery, .gallery, [class*="gallery"] {
        background: #ffffff !important;
    }
    /* Video 和 Image */
    .gr-video, .gr-image, .video-container, .image-container,
    [class*="video"], [class*="image"] {
        background: #f8fafc !important;
    }
    /* Markdown */
    .gr-markdown, .markdown, .prose, [class*="markdown"] {
        color: #1e293b !important;
    }
    .gr-markdown h1, .gr-markdown h2, .gr-markdown h3,
    .markdown h1, .markdown h2, .markdown h3 {
        color: #1e293b !important;
    }
    /* 状态徽章 */
    .status-badge {
        background: #f1f5f9 !important;
        color: #475569 !important;
        padding: 4px 8px !important;
        border-radius: 6px !important;
    }
    /* JSON 显示 */
    .json, .gr-json, [class*="json"] {
        background: #f8fafc !important;
        color: #1e293b !important;
    }
    .json pre, .gr-json pre {
        background: #f8fafc !important;
        color: #1e293b !important;
    }
    /* 按钮文字 - 保持对比度 */
    button.primary, .gr-button.primary {
        color: #ffffff !important;
    }
    button.secondary, .gr-button.secondary {
        color: #475569 !important;
        background: #ffffff !important;
    }
    button.stop, .gr-button.stop {
        color: #ffffff !important;
    }

    /* ========== 场景列表 ========== */
    .sortable-scene-container {
        display: flex;
        flex-direction: column;
        gap: 6px;
        max-height: 500px;
        overflow-y: auto;
        padding: 10px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
    }
    .sortable-scene-container::-webkit-scrollbar {
        width: 6px;
    }
    .sortable-scene-container::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 3px;
    }
    .scene-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        cursor: grab;
        transition: all 0.2s ease;
    }
    .scene-item:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
        transform: translateX(2px);
    }
    .scene-item.selected {
        border-color: #667eea;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    }
    .scene-drag-handle { color: #94a3b8; font-size: 14px; cursor: grab; }
    .scene-index {
        min-width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f1f5f9;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
    }
    .scene-thumb {
        width: 48px;
        height: 32px;
        background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
        border-radius: 4px;
        flex-shrink: 0;
        background-size: cover;
    }
    .scene-info { flex: 1; min-width: 0; }
    .scene-id { font-size: 12px; font-weight: 600; color: #1e293b; }
    .scene-desc { font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
    .scene-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .scene-duration {
        font-size: 11px;
        color: #64748b;
        background: #f1f5f9;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .scene-status { font-size: 12px; }
    .scene-list-empty {
        padding: 40px 20px;
        text-align: center;
        color: #94a3b8;
        font-size: 13px;
    }
    .drag-hint {
        margin-top: 8px;
        font-size: 11px;
        color: #94a3b8;
        text-align: center;
    }
    mark { background: #fef08a; padding: 1px 4px; border-radius: 3px; }

    /* ========== 日志区域 ========== */
    #realtime-log textarea {
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace !important;
        font-size: 11px !important;
        background: #1e293b !important;
        color: #e2e8f0 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }

    /* ========== 文件上传区域 ========== */
    .gr-file, .gr-upload {
        border: 2px dashed #e2e8f0 !important;
        border-radius: 10px !important;
        background: #f8fafc !important;
        transition: all 0.2s ease !important;
    }
    .gr-file:hover, .gr-upload:hover {
        border-color: #667eea !important;
        background: rgba(102, 126, 234, 0.02) !important;
    }

    /* ========== 视频预览 ========== */
    .gr-video, .gr-image {
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* ========== 滑块 ========== */
    .gr-slider input[type="range"] {
        accent-color: #667eea !important;
    }

    /* ========== 复选框/单选框 ========== */
    .gr-checkbox input, .gr-radio input {
        accent-color: #667eea !important;
    }

    /* ========== 标签页内标签 ========== */
    .gr-tab-nav button {
        border-radius: 8px 8px 0 0 !important;
        font-weight: 500 !important;
    }
    .gr-tab-nav button.selected {
        background: #fff !important;
        color: #667eea !important;
    }

    /* ========== 响应式布局 ========== */
    @media (max-width: 1024px) {
        .main-layout { flex-direction: column !important; }
        .sidebar {
            max-width: 100% !important;
            min-width: 100% !important;
            min-height: auto !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            padding: 8px !important;
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
            padding: 12px !important;
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
