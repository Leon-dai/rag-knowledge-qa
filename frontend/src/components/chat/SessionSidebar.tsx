import { Button, List, Typography, Popconfirm, Tooltip } from 'antd'
import { PlusOutlined, DeleteOutlined, MenuFoldOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import { useAuthStore } from '../../stores/authStore'
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
  const { user } = useAuthStore()

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

  // 按时间分组
  const groupedSessions = {
    today: sessions.filter(s => dayjs(s.updated_at).isSame(dayjs(), 'day')),
    yesterday: sessions.filter(s => dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    week: sessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day')) && !dayjs(s.updated_at).isSame(dayjs(), 'day') && !dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    month: sessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(30, 'day')) && !dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day'))),
  }

  return (
    <div style={{
      width: collapsed ? 0 : 280,
      minWidth: collapsed ? 0 : 280,
      borderRight: collapsed ? 'none' : '1px solid #f0f0f0',
      background: '#fafafa',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      transition: 'all 0.3s ease',
    }}>
      {/* Logo 区域 */}
      <div style={{
        padding: '16px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28,
            height: 28,
            background: '#1677ff',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 16,
          }}>

          </div>
          <Text strong style={{ fontSize: 16, color: '#1677ff' }}>AI 搜索</Text>
        </div>
        <Tooltip title="折叠侧边栏">
          <Button
            type="text"
            size="small"
            icon={<MenuFoldOutlined />}
            onClick={onToggle}
          />
        </Tooltip>
      </div>

      {/* 新建对话按钮 */}
      <div style={{ padding: '12px 16px' }}>
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

      {/* 底部用户信息 */}
      {user && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: '#1677ff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 12,
          }}>
            {user.username?.charAt(0).toUpperCase()}
          </div>
          <Text style={{ fontSize: 13 }}>{user.username}</Text>
        </div>
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
