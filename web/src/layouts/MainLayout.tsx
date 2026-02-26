import { useState } from 'react'
import { Outlet, useNavigate, useLocation, useParams } from 'react-router-dom'
import { Layout, Menu, theme, Typography, Badge } from 'antd'
import {
  ProjectOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  SettingOutlined,
  UnorderedListOutlined,
  ScissorOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'

const { Header, Sider, Content } = Layout
const { Title } = Typography

function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { projectName } = useParams()
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken()

  // 主菜单项
  const mainMenuItems: MenuProps['items'] = [
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: '项目管理',
    },
    {
      key: '/tasks',
      icon: <UnorderedListOutlined />,
      label: '任务队列',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
  ]

  // 项目内菜单项
  const projectMenuItems: MenuProps['items'] = projectName ? [
    {
      key: `/projects/${projectName}/scenes`,
      icon: <VideoCameraOutlined />,
      label: '分镜管理',
    },
    {
      key: `/projects/${projectName}/characters`,
      icon: <TeamOutlined />,
      label: '角色管理',
    },
    {
      key: `/projects/${projectName}/generation`,
      icon: <PlayCircleOutlined />,
      label: '生成控制',
    },
    {
      key: `/projects/${projectName}/preview`,
      icon: <EyeOutlined />,
      label: '预览',
    },
    {
      key: `/projects/${projectName}/editor`,
      icon: <ScissorOutlined />,
      label: '视频编辑',
    },
  ] : []

  const menuItems = projectName ? [...projectMenuItems, { type: 'divider' as const }, ...mainMenuItems] : mainMenuItems

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    navigate(e.key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          borderRight: '1px solid #f0f0f0',
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
            {collapsed ? '📹' : '小说转视频'}
          </Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'all 0.2s' }}>
        <Header style={{ 
          padding: '0 24px', 
          background: colorBgContainer,
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            {projectName && (
              <Typography.Text strong>项目: {projectName}</Typography.Text>
            )}
          </div>
          <Badge count={0} showZero={false}>
            <UnorderedListOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
          </Badge>
        </Header>
        <Content style={{
          margin: 24,
          padding: 24,
          minHeight: 280,
          background: colorBgContainer,
          borderRadius: borderRadiusLG,
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout

