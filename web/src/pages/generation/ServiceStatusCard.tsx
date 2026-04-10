import { Card, Row, Col, Space, Typography, Button } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ServiceStatus } from '../../api/generation'

const { Text } = Typography

interface ServiceStatusCardProps {
  serviceStatus: ServiceStatus | null
  onRefresh: () => void
}

const SERVICE_TIPS: Record<string, string> = {
  Ollama: '请检查 Ollama 是否已启动 (默认端口 11434)。可运行 "ollama serve" 启动服务。',
  ComfyUI: '请检查 ComfyUI 是否已启动 (默认端口 8188)。确保 ComfyUI 的 API 端点正常运行。',
  CosyVoice: '请检查 CosyVoice 服务是否已启动 (默认端口 9880)。如不需要语音合成可忽略。',
}

function ServiceItem({ name, available, extra }: { name: string; available: boolean; extra?: string }) {
  return (
    <Col xs={12} sm={8} md={6}>
      <Card size="small">
        <Space>
          {available ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 20 }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
          )}
          <div>
            <Text strong>{name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {available ? extra || '在线' : '离线'}
            </Text>
            {!available && (
              <>
                <br />
                <Text type="danger" style={{ fontSize: 11 }}>
                  {SERVICE_TIPS[name] || '请检查服务是否正常运行。'}
                </Text>
              </>
            )}
          </div>
        </Space>
      </Card>
    </Col>
  )
}

export default function ServiceStatusCard({ serviceStatus, onRefresh }: ServiceStatusCardProps) {
  return (
    <Card
      title="服务状态"
      style={{ marginBottom: 24 }}
      extra={<Button icon={<ReloadOutlined />} onClick={onRefresh} size="small">刷新</Button>}
    >
      <Row gutter={[16, 16]}>
        {serviceStatus && (
          <>
            <ServiceItem name="Ollama" available={serviceStatus.ollama.available} extra={serviceStatus.ollama.model} />
            <ServiceItem name="ComfyUI" available={serviceStatus.comfyui.available} extra={`队列: ${serviceStatus.comfyui.queue_size}`} />
            <ServiceItem name="CosyVoice" available={serviceStatus.cosyvoice.available} />
          </>
        )}
      </Row>
    </Card>
  )
}
