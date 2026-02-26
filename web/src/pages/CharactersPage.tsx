import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Space,
  Avatar,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tag,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SoundOutlined,
  ReloadOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { characterApi, VoiceInfo } from '../api/characters'
import type { Character } from '../types'

const { Title, Paragraph } = Typography

function CharactersPage() {
  const { projectName } = useParams<{ projectName: string }>()
  const [characters, setCharacters] = useState<Character[]>([])
  const [voices, setVoices] = useState<VoiceInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [form] = Form.useForm()

  const fetchCharacters = async () => {
    if (!projectName) return
    try {
      setLoading(true)
      const data = await characterApi.list(projectName)
      setCharacters(data.characters)
    } catch (error) {
      message.error('获取角色列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchVoices = async () => {
    try {
      const data = await characterApi.getVoices()
      setVoices(data)
    } catch (error) {
      console.error('获取音色列表失败')
    }
  }

  useEffect(() => {
    fetchCharacters()
    fetchVoices()
  }, [projectName])

  const handleCreate = () => {
    setIsCreating(true)
    setEditingCharacter(null)
    form.resetFields()
    setEditModalVisible(true)
  }

  const handleEdit = (character: Character) => {
    setIsCreating(false)
    setEditingCharacter(character)
    // 将后端数据结构转换为表单格式
    form.setFieldsValue({
      name: character.name,
      aliases: character.aliases?.join(', ') || '',
      gender: character.appearance?.gender || '',
      hair: character.appearance?.hair || '',
      eyes: character.appearance?.eyes || '',
      clothing: character.appearance?.clothing || '',
      features: character.appearance?.features || '',
      sd_prompt: character.sd_prompt || '',
      sd_negative: character.sd_negative || '',
      voice_id: character.voice?.voice_id || '',
    })
    setEditModalVisible(true)
  }

  const handleSave = async (values: Record<string, string>) => {
    if (!projectName) return
    try {
      // 将表单数据转换为后端期望的格式
      const characterData: Partial<Character> = {
        name: values.name,
        aliases: values.aliases ? values.aliases.split(/[,，]/).map(s => s.trim()).filter(Boolean) : [],
        appearance: {
          gender: values.gender || 'unknown',
          hair: values.hair || '',
          eyes: values.eyes || '',
          clothing: values.clothing || '',
          features: values.features || '',
        },
        sd_prompt: values.sd_prompt || '',
        sd_negative: values.sd_negative || '',
        voice: values.voice_id ? { voice_id: values.voice_id } : undefined,
      }

      if (isCreating) {
        await characterApi.create(projectName, characterData)
        message.success('创建成功')
      } else if (editingCharacter) {
        await characterApi.update(projectName, editingCharacter.id, characterData)
        message.success('保存成功')
      }
      setEditModalVisible(false)
      fetchCharacters()
    } catch (error) {
      message.error(isCreating ? '创建失败' : '保存失败')
    }
  }

  const handleDelete = async (characterId: string) => {
    if (!projectName) return
    try {
      await characterApi.delete(projectName, characterId)
      message.success('删除成功')
      fetchCharacters()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handlePreviewVoice = async (voiceId: string) => {
    if (!projectName) return
    try {
      const result = await characterApi.previewVoice(projectName, voiceId, '您好，这是一段语音测试。')
      if (result.audio_data) {
        // 后端返回的是 Base64 编码的音频数据
        const audioBlob = new Blob(
          [Uint8Array.from(atob(result.audio_data), c => c.charCodeAt(0))],
          { type: 'audio/wav' }
        )
        const audioUrl = URL.createObjectURL(audioBlob)
        const audio = new Audio(audioUrl)
        audio.play()
      } else {
        message.warning(result.message || '语音合成失败')
      }
    } catch (error) {
      message.error('语音试听失败')
    }
  }

  // 获取角色的描述信息（优先显示外貌特征）
  const getCharacterDescription = (char: Character): string => {
    if (char.appearance?.features) return char.appearance.features
    if (char.sd_prompt) return char.sd_prompt
    return '无描述'
  }

  // 获取角色头像图片路径
  const getPortraitUrl = (char: Character): string | undefined => {
    if (char.images && char.images.length > 0) {
      // 假设图片路径需要转换为静态文件 URL
      return `/static/projects/${projectName}/characters/${char.id}/${char.images[0].split(/[\\/]/).pop()}`
    }
    return undefined
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
        <Title level={3} style={{ margin: 0 }}>角色管理 - {projectName}</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchCharacters}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>添加角色</Button>
        </Space>
      </div>

      {characters.length === 0 ? (
        <Empty description="暂无角色" />
      ) : (
        <Row gutter={[16, 16]}>
          {characters.map((char) => (
            <Col xs={24} sm={12} md={8} lg={6} key={char.id}>
              <Card
                actions={[
                  <EditOutlined key="edit" onClick={() => handleEdit(char)} />,
                  <SoundOutlined key="voice" onClick={() => char.voice?.voice_id && handlePreviewVoice(char.voice.voice_id)} />,
                  <Popconfirm key="delete" title="确定删除?" onConfirm={() => handleDelete(char.id)}>
                    <DeleteOutlined />
                  </Popconfirm>,
                ]}
              >
                <Card.Meta
                  avatar={
                    getPortraitUrl(char) ? (
                      <Avatar size={64} src={getPortraitUrl(char)} />
                    ) : (
                      <Avatar size={64} icon={<UserOutlined />} />
                    )
                  }
                  title={
                    <Space>
                      {char.name}
                      {char.appearance?.gender && (
                        <Tag color={char.appearance.gender === 'female' ? 'pink' : 'blue'}>
                          {char.appearance.gender === 'female' ? '女' : char.appearance.gender === 'male' ? '男' : char.appearance.gender}
                        </Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>
                      {getCharacterDescription(char)}
                    </Paragraph>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Modal
        title={isCreating ? '添加角色' : `编辑角色 - ${editingCharacter?.name}`}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="角色名称" rules={[{ required: true, message: '请输入角色名称' }]}>
                <Input placeholder="角色名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="aliases" label="别名（逗号分隔）">
                <Input placeholder="别名1, 别名2" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="gender" label="性别">
                <Select placeholder="选择性别" allowClear>
                  <Select.Option value="male">男</Select.Option>
                  <Select.Option value="female">女</Select.Option>
                  <Select.Option value="unknown">未知</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="hair" label="发型">
                <Input placeholder="如: black long hair" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="eyes" label="眼睛">
                <Input placeholder="如: brown eyes" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="clothing" label="服装">
                <Input placeholder="如: white hanfu robe" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="features" label="特征">
                <Input placeholder="如: handsome young man" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="sd_prompt" label="SD 正向提示词">
            <Input.TextArea rows={2} placeholder="用于生成立绘的提示词" />
          </Form.Item>

          <Form.Item name="sd_negative" label="SD 负向提示词">
            <Input.TextArea rows={2} placeholder="如: ugly, deformed, bad anatomy" />
          </Form.Item>

          <Form.Item name="voice_id" label="配音音色">
            <Select placeholder="选择音色" allowClear>
              {voices.map((voice) => (
                <Select.Option key={voice.id} value={voice.id}>
                  {voice.name} ({voice.gender})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">{isCreating ? '创建' : '保存'}</Button>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CharactersPage

