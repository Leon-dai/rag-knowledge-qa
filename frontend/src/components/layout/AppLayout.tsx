import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, Avatar, Typography } from 'antd'
import {
  MessageOutlined,
  UserOutlined,
  LogoutOutlined,
  KeyOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useAuthStore } from '../../stores/authStore'

const { Header, Content } = Layout
const { Text } = Typography

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, fetchMe } = useAuthStore()

  useEffect(() => {
    if (!user) fetchMe()
  }, [user, fetchMe])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'role',
      label: <Text type="secondary">{user?.role === 'admin' ? '管理员' : '普通用户'}</Text>,
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'changePassword',
      icon: <KeyOutlined />,
      label: '修改密码',
      onClick: () => navigate('/profile/change-password'),
    },
    ...(user?.role === 'admin'
      ? [{
          key: 'admin',
          icon: <SettingOutlined />,
          label: '管理后台',
          onClick: () => navigate('/admin'),
        }]
      : []),
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
      danger: true,
    },
  ]

  const menuItems: MenuProps['items'] = [
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: '知识库问答',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <Text strong style={{ fontSize: 18 }}>📚 知识库问答系统</Text>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname.startsWith('/admin') ? '' : '/chat']}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ border: 'none' }}
          />
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Button type="text" icon={<Avatar icon={<UserOutlined />} size="small" />}>
            {user?.username || '用户'}
          </Button>
        </Dropdown>
      </Header>
      <Content>
        <Outlet />
      </Content>
    </Layout>
  )
}
