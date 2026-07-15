import { useEffect } from 'react'
import { Button, List, Typography, Popconfirm, Tooltip, Dropdown, Avatar } from 'antd'
import { PlusOutlined, DeleteOutlined, MenuFoldOutlined, UserOutlined, LogoutOutlined, KeyOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import { useAuthStore } from '../../stores/authStore'
import type { MenuProps } from 'antd'
import dayjs from 'dayjs'

const { Text } = Typography

interface Props {
  collapsed: boolean
  onToggle: () => void
}

export default function SessionSidebar({ collapsed, onToggle }: Props) {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()
  const { sessions, createSession, deleteSession } = useChatStore()
  const { user, logout, fetchMe } = useAuthStore()

  // 确保用户信息已加载
  useEffect(() => {
    if (!user) fetchMe()
  }, [user, fetchMe])

  const handleCreate = async () => {
    await createSession()
    const { currentSession } = useChatStore.getState()
    if (currentSession) {
      navigate(`/chat/${currentSession.id}`)
    }
  }

  const handleDelete = async (id: string) => {
    await deleteSession(id)
    if (sessionId === id) {
      navigate('/chat')
    }
  }

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

  // 按时间分组
  const groupedSessions = {
    today: sessions.filter(s => dayjs(s.updated_at).isSame(dayjs(), 'day')),
    yesterday: sessions.filter(s => dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    week: sessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day')) && !dayjs(s.updated_at).isSame(dayjs(), 'day') && !dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    month: sessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(30, 'day')) && !dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day'))),
  }

  return (
    <div style={{
      width: 280,
      height: '100%',
      borderRight: '1px solid #f0f0f0',
      background: '#fafafa',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      position: 'relative',
      transform: collapsed ? 'translateX(-100%)' : 'translateX(0)',
      transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease',
      opacity: collapsed ? 0 : 1,
      flexShrink: 0,
    }}>
      {/* Logo 区域 */}
      <div style={{
        padding: '16px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 60,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
          <div style={{
            width: 28,
            height: 28,
            background: 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 14,
            flexShrink: 0,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <Text strong style={{ fontSize: 16, color: '#1677ff', whiteSpace: 'nowrap' }}>AI 搜索</Text>
        </div>
        <Tooltip title="折叠侧边栏">
          <Button
            type="text"
            size="small"
            icon={<MenuFoldOutlined />}
            onClick={onToggle}
            style={{ flexShrink: 0 }}
          />
        </Tooltip>
      </div>

      {/* 新建对话按钮 */}
      <div style={{ padding: '12px 16px', flexShrink: 0 }}>
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleCreate}
          block
          style={{ borderRadius: 8 }}
        >
          开启新对话
        </Button>
      </div>

      {/* 会话列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
        {groupedSessions.today.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>今天</Text>
            <SessionList sessions={groupedSessions.today} onDelete={handleDelete} onNavigate={navigate} sessionId={sessionId} />
          </>
        )}
        {groupedSessions.yesterday.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>昨天</Text>
            <SessionList sessions={groupedSessions.yesterday} onDelete={handleDelete} onNavigate={navigate} sessionId={sessionId} />
          </>
        )}
        {groupedSessions.week.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>7 天内</Text>
            <SessionList sessions={groupedSessions.week} onDelete={handleDelete} onNavigate={navigate} sessionId={sessionId} />
          </>
        )}
        {groupedSessions.month.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>30 天内</Text>
            <SessionList sessions={groupedSessions.month} onDelete={handleDelete} onNavigate={navigate} sessionId={sessionId} />
          </>
        )}
      </div>

      {/* 底部用户信息 - 可点击 */}
      {user && (
        <Dropdown
          menu={{
            items: userMenuItems,
            style: { width: 160 },
          }}
          placement="topLeft"
          trigger={['click']}
        >
          <div style={{
            padding: '12px 16px',
            borderTop: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            cursor: 'pointer',
            transition: 'background 0.2s',
            flexShrink: 0,
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#f0f0f0'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <Avatar size="small" icon={<UserOutlined />} style={{ background: '#1677ff' }} />
            <Text style={{ fontSize: 13 }}>{user.username}</Text>
          </div>
        </Dropdown>
      )}
    </div>
  )
}

// 会话列表组件
function SessionList({ sessions, onDelete, onNavigate, sessionId }: {
  sessions: any[]
  onDelete: (id: string) => void
  onNavigate: (path: string) => void
  sessionId: string | undefined
}) {
  return (
    <List
      dataSource={sessions}
      renderItem={(session) => (
        <List.Item
          onClick={() => onNavigate(`/chat/${session.id}`)}
          style={{
            cursor: 'pointer',
            padding: '10px 12px',
            marginBottom: 4,
            borderRadius: 8,
            background: sessionId === session.id ? '#e6f4ff' : 'transparent',
            borderLeft: sessionId === session.id ? '3px solid #1677ff' : '3px solid transparent',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (sessionId !== session.id) {
              e.currentTarget.style.background = '#f5f5f5'
            }
          }}
          onMouseLeave={(e) => {
            if (sessionId !== session.id) {
              e.currentTarget.style.background = 'transparent'
            }
          }}
        >
          <div style={{ width: '100%', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text
                strong
                ellipsis={{ tooltip: session.title }}
                style={{ maxWidth: 180, fontSize: 13 }}
              >
                {session.title}
              </Text>
              <Popconfirm
                title="确定删除此对话？"
                onConfirm={(e) => {
                  e?.stopPropagation()
                  onDelete(session.id)
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                  style={{ opacity: 0.6 }}
                />
              </Popconfirm>
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {dayjs(session.updated_at).format('MM-DD HH:mm')}
              {' · '}
              {session.message_count} 条消息
            </Text>
          </div>
        </List.Item>
      )}
      locale={{ emptyText: null }}
    />
  )
}