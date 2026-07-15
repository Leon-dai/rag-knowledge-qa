import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Dropdown, Avatar, Typography } from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  KeyOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { useAuthStore } from '../../stores/authStore'

const { Text } = Typography

export default function AppLayout() {
  const navigate = useNavigate()
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

  return (
    <div style={{ height: '100vh', overflow: 'hidden' }}>
      <Outlet />

      {/* 用户菜单 - 放在聊天页面内部 */}
      {user && (
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <div style={{
            position: 'fixed',
            top: 16,
            right: 16,
            zIndex: 1000,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 12px',
            borderRadius: 20,
            background: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}>
            <Avatar icon={<UserOutlined />} size="small" />
            <Text style={{ fontSize: 13 }}>{user?.username || '用户'}</Text>
          </div>
        </Dropdown>
      )}
    </div>
  )
}
