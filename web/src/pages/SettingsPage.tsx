import { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Typography,
  Tabs,
  message,
  Spin,
} from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'
import { settingsApi } from '../api/settings'
import { showApiError } from '../api/client'
import type { AppSettings } from '../types'

const { Title } = Typography

function SettingsPage() {
  const [, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [localForm] = Form.useForm()
  const [apiForm] = Form.useForm()
  const [videoForm] = Form.useForm()

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const response = await settingsApi.getAll()
      setSettings(response.settings)
      localForm.setFieldsValue(response.settings.local)
      apiForm.setFieldsValue(response.settings.api)
      videoForm.setFieldsValue(response.settings.video)
    } catch (error) {
      showApiError(error, '获取设置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  const handleSaveLocal = async (values: AppSettings['local']) => {
    try {
      setSaving(true)
      await settingsApi.updateLocal(values)
      message.success('本地服务配置已保存')
    } catch (error) {
      showApiError(error, '保存本地服务配置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveApi = async (values: AppSettings['api']) => {
    try {
      setSaving(true)
      await settingsApi.updateApi(values)
      message.success('API配置已保存')
    } catch (error) {
      showApiError(error, '保存API配置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveVideo = async (values: AppSettings['video']) => {
    try {
      setSaving(true)
      await settingsApi.updateVideo(values)
      message.success('视频配置已保存')
    } catch (error) {
      showApiError(error, '保存视频配置失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  const tabItems = [
    {
      key: 'local',
      label: '本地服务',
      children: (
        <Form form={localForm} layout="vertical" onFinish={handleSaveLocal}>
          <Form.Item name="ollama_url" label="Ollama 地址">
            <Input placeholder="http://localhost:11434" />
          </Form.Item>
          <Form.Item name="ollama_model" label="Ollama 模型">
            <Input placeholder="glm4:9b" />
          </Form.Item>
          <Form.Item name="comfyui_url" label="ComfyUI 地址">
            <Input placeholder="http://localhost:8188" />
          </Form.Item>
          <Form.Item name="cosyvoice_url" label="CosyVoice 地址">
            <Input placeholder="http://localhost:9880" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'api',
      label: 'API 配置',
      children: (
        <Form form={apiForm} layout="vertical" onFinish={handleSaveApi}>
          <Form.Item name="video_provider" label="视频生成服务">
            <Select>
              <Select.Option value="jimeng">即梦 AI</Select.Option>
              <Select.Option value="kling">可灵 AI</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="video_api_key" label="API Key">
            <Input.Password placeholder="输入 API Key" />
          </Form.Item>
          <Form.Item name="use_idle_time" label="使用闲时优惠" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: 'video',
      label: '视频输出',
      children: (
        <Form form={videoForm} layout="vertical" onFinish={handleSaveVideo}>
          <Form.Item name="resolution" label="分辨率">
            <Select>
              <Select.Option value="1920x1080">1920x1080 (1080p)</Select.Option>
              <Select.Option value="1280x720">1280x720 (720p)</Select.Option>
              <Select.Option value="854x480">854x480 (480p)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="fps" label="帧率">
            <InputNumber min={15} max={60} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={saving}>
              保存
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>系统设置</Title>
        <Button icon={<ReloadOutlined />} onClick={fetchSettings}>刷新</Button>
      </div>

      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  )
}

export default SettingsPage

