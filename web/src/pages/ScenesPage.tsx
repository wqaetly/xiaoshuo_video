import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Image,
  Tag,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  message,
  Popconfirm,
} from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { sceneApi } from '../api/scenes'
import type { Scene } from '../types'

const { Title, Text, Paragraph } = Typography

function ScenesPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [scenes, setScenes] = useState<Scene[]>([])
  const [loading, setLoading] = useState(true)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingScene, setEditingScene] = useState<Scene | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [form] = Form.useForm()

  const fetchScenes = async () => {
    if (!projectName) return
    try {
      setLoading(true)
      const data = await sceneApi.list(projectName)
      setScenes(data.scenes)
    } catch (error) {
      message.error('获取场景列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScenes()
  }, [projectName])

  const handleAnalyze = async () => {
    if (!projectName) return
    try {
      setAnalyzing(true)
      await sceneApi.analyze(projectName)
      message.success('分镜分析任务已启动')
      fetchScenes()
    } catch (error) {
      message.error('启动分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleEdit = (scene: Scene) => {
    setEditingScene(scene)
    form.setFieldsValue(scene)
    setEditModalVisible(true)
  }

  const handleSave = async (values: Partial<Scene>) => {
    if (!projectName || !editingScene) return
    try {
      await sceneApi.update(projectName, editingScene.id, values)
      message.success('保存成功')
      setEditModalVisible(false)
      fetchScenes()
    } catch (error) {
      message.error('保存失败')
    }
  }

  const handleDelete = async (sceneId: string) => {
    if (!projectName) return
    try {
      await sceneApi.delete(projectName, sceneId)
      message.success('删除成功')
      fetchScenes()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const getStatusTag = (status?: string) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>
      case 'generating':
        return <Tag color="processing">生成中</Tag>
      case 'error':
        return <Tag color="error">错误</Tag>
      default:
        return <Tag>待处理</Tag>
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>分镜管理 - {projectName}</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchScenes}>刷新</Button>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleAnalyze} loading={analyzing}>
            分析小说
          </Button>
        </Space>
      </div>

      {scenes.length === 0 ? (
        <Empty description="暂无场景，请先上传小说并点击&quot;分析小说&quot;" />
      ) : (
        <Row gutter={[16, 16]}>
          {scenes.map((scene) => (
            <Col xs={24} sm={12} md={8} lg={6} key={scene.id}>
              <Card
                cover={
                  scene.image_url ? (
                    <Image src={scene.image_url} alt={scene.title} height={160} style={{ objectFit: 'cover' }} />
                  ) : (
                    <div style={{ height: 160, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Text type="secondary">暂无图片</Text>
                    </div>
                  )
                }
                actions={[
                  <EditOutlined key="edit" onClick={() => handleEdit(scene)} />,
                  <Popconfirm key="delete" title="确定删除?" onConfirm={() => handleDelete(scene.id)}>
                    <DeleteOutlined />
                  </Popconfirm>,
                ]}
              >
                <Card.Meta
                  title={
                    <Space>
                      <span>#{scene.scene_number}</span>
                      {getStatusTag(scene.status)}
                    </Space>
                  }
                  description={
                    <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                      {scene.description || scene.narration || '无描述'}
                    </Paragraph>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={`编辑场景 #${editingScene?.scene_number}`}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="title" label="标题">
            <Input placeholder="场景标题" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="场景描述" />
          </Form.Item>
          <Form.Item name="narration" label="旁白">
            <Input.TextArea rows={3} placeholder="旁白文本" />
          </Form.Item>
          <Form.Item name="dialogue" label="对白">
            <Input.TextArea rows={3} placeholder="对白内容" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">保存</Button>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ScenesPage

