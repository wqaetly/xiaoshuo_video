import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  Switch,
  message,
  Spin,
  Empty,
  Popconfirm,
  Progress,
} from 'antd'
import {
  PlusOutlined,
  FolderOpenOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { projectApi } from '../api/projects'
import { showApiError } from '../api/client'
import type { Project } from '../types'

const { Title, Text } = Typography

// 预设风格选项
const STYLE_OPTIONS = [
  { value: 'anime', label: '动漫风格' },
  { value: 'realistic', label: '写实风格' },
  { value: 'cinematic', label: '电影风格' },
  { value: 'watercolor', label: '水彩风格' },
  { value: 'illustration', label: '插画风格' },
]

interface CreateFormValues {
  name: string
  style: string
  quickGenerate: boolean
}

function ProjectsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [creating, setCreating] = useState(false)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [form] = Form.useForm<CreateFormValues>()

  // 监听快速生成开关状态
  const quickGenerate = Form.useWatch('quickGenerate', form) ?? true

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const data = await projectApi.list()
      setProjects(data.projects)
    } catch (error) {
      showApiError(error, '获取项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreate = async (values: CreateFormValues) => {
    // 检查是否上传了文件
    if (fileList.length === 0) {
      message.error('请上传文本文件')
      return
    }

    const file = fileList[0].originFileObj
    if (!file) {
      message.error('文件无效，请重新选择')
      return
    }

    try {
      setCreating(true)

      if (values.quickGenerate) {
        // 快速生成模式：创建并立即启动生成
        const result = await projectApi.quickCreate(values.name, file, values.style)
        if (result.generation_started) {
          message.success('项目创建成功，正在生成中...')
          // 跳转到生成页面
          navigate(`/projects/${result.name}/generation`)
        } else {
          message.warning(`项目创建成功，但启动生成失败: ${result.generation_message}`)
          navigate(`/projects/${result.name}/scenes`)
        }
      } else {
        // 普通模式：只创建项目
        await projectApi.create(values.name, file, values.style)
        message.success('项目创建成功')
        fetchProjects()
      }

      setCreateModalVisible(false)
      form.resetFields()
      setFileList([])
    } catch (error) {
      showApiError(error, '创建项目失败')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (projectName: string) => {
    try {
      await projectApi.delete(projectName)
      message.success('项目已删除')
      fetchProjects()
    } catch (error) {
      showApiError(error, '删除项目失败')
    }
  }

  const handleOpenProject = (projectName: string) => {
    navigate(`/projects/${projectName}/scenes`)
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
        <Title level={3} style={{ margin: 0 }}>项目管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          新建项目
        </Button>
      </div>

      {projects.length === 0 ? (
        <Empty description="暂无项目" />
      ) : (
        <Row gutter={[16, 16]}>
          {projects.map((project) => (
            <Col xs={24} sm={12} md={8} lg={6} key={project.name}>
              <Card
                hoverable
                actions={[
                  <FolderOpenOutlined key="open" onClick={() => handleOpenProject(project.name)} />,
                  <Popconfirm
                    key="delete"
                    title="确定删除此项目?"
                    onConfirm={() => handleDelete(project.name)}
                  >
                    <DeleteOutlined />
                  </Popconfirm>,
                ]}
              >
                <Card.Meta
                  title={project.name}
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text type="secondary">{project.description || '无描述'}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {project.scene_count || 0} 个场景
                      </Text>
                      {project.progress !== undefined && (
                        <Progress percent={Math.round(project.progress * 100)} size="small" />
                      )}
                    </Space>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title="新建项目"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          setFileList([])
          form.resetFields()
        }}
        footer={null}
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ style: 'anime', quickGenerate: true }}
        >
          <Form.Item
            name="name"
            label="项目名称"
            rules={[
              { required: true, message: '请输入项目名称' },
              { pattern: /^[^\\/:*?"<>|]+$/, message: '项目名称不能包含特殊字符' }
            ]}
          >
            <Input placeholder="输入项目名称（如：歌词视频）" />
          </Form.Item>

          <Form.Item
            label="文本文件"
            required
            extra="支持 .txt 格式的小说、歌词、剧本等文本文件"
          >
            <Upload
              accept=".txt"
              maxCount={1}
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: newFileList }) => {
                setFileList(newFileList)
                // 自动填充项目名称（如果用户未输入）
                if (newFileList.length > 0 && !form.getFieldValue('name')) {
                  const fileName = newFileList[0].name.replace(/\.txt$/i, '')
                  form.setFieldValue('name', fileName)
                }
              }}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="style"
            label="视频风格"
          >
            <Select options={STYLE_OPTIONS} />
          </Form.Item>

          <Form.Item
            name="quickGenerate"
            valuePropName="checked"
            extra="开启后，创建项目时将自动开始生成流程"
          >
            <Space>
              <Switch />
              <Text><ThunderboltOutlined style={{ color: '#faad14' }} /> 快速生成模式</Text>
            </Space>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => {
                setCreateModalVisible(false)
                setFileList([])
                form.resetFields()
              }}>
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={creating}
                icon={quickGenerate ? <ThunderboltOutlined /> : <PlusOutlined />}
              >
                {creating ? '处理中...' : (quickGenerate ? '创建并生成' : '创建项目')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectsPage

