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
} from '@ant-design/icons'
import { projectApi } from '../api/projects'
import type { Project } from '../types'

const { Title, Text } = Typography

function ProjectsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const data = await projectApi.list()
      setProjects(data.projects)
    } catch (error) {
      message.error('获取项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreate = async (values: { name: string; description?: string }) => {
    try {
      setCreating(true)
      await projectApi.create(values.name, values.description)
      message.success('项目创建成功')
      setCreateModalVisible(false)
      form.resetFields()
      fetchProjects()
    } catch (error) {
      message.error('创建项目失败')
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
      message.error('删除项目失败')
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
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="输入项目名称" />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={3} placeholder="输入项目描述（可选）" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={creating}>
                创建
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectsPage

