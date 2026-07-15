import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Typography } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  TeamOutlined,
  SettingOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'

const { Sider, Content, Header } = Layout
const { Text } = Typography

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems: MenuProps['items'] = [
    {
      key: '/admin',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/admin/documents',
      icon: <FileTextOutlined />,
      label: '知识库管理',
    },
    {
      key: '/admin/users',
      icon: <TeamOutlined />,
      label: '用户管理',
    },
    {
      key: '/admin/models',
      icon: <SettingOutlined />,
      label: '模型设置',
    },
  ]

  const selectedKey = menuItems
    .map((m) => m!.key as string)
    .filter((k) => location.pathname.startsWith(k))
    .sort((a, b) => b.length - a.length)[0] || '/admin'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="dark"
        width={220}
        style={{ position: 'fixed', left: 0, top: 0, bottom: 0 }}
      >
        <div style={{ padding: '20px 16px', textAlign: 'center' }}>
          <Text strong style={{ color: '#fff', fontSize: 16 }}>⚙️ 管理后台</Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout style={{ marginLeft: 220 }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
        }}>
          <Button
            type="link"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/chat')}
          >
            返回问答
          </Button>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
