import { useEffect, useState } from 'react'
import { Button, Typography, Tooltip, Dropdown, Avatar, Input, message, Spin } from 'antd'
import { PlusOutlined, MenuFoldOutlined, UserOutlined, LogoutOutlined, KeyOutlined, SettingOutlined, MoreOutlined, PushpinOutlined, ShareAltOutlined, DeleteOutlined, EditOutlined, CheckOutlined, CloseOutlined, SearchOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import { useAuthStore } from '../../stores/authStore'
import { chatAPI } from '../../api/chat'
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
  const { sessions, createSession, deleteSession, renameSession } = useChatStore()
  const { user, logout, fetchMe } = useAuthStore()

  // 确保用户信息已加载
  useEffect(() => {
    if (!user) fetchMe()
  }, [user, fetchMe])

  // 置顶会话列表
  const [pinnedIds, setPinnedIds] = useState<string[]>([])

  // 搜索状态
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[] | null>(null)
  const [searching, setSearching] = useState(false)

  const handleSearch = async (q: string) => {
    setSearchQuery(q)
    if (!q.trim()) {
      setSearchResults(null)
      return
    }
    setSearching(true)
    try {
      const res = await chatAPI.searchSessions(q.trim())
      setSearchResults(res.data.items || [])
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleCloseSearch = () => {
    setSearchOpen(false)
    setSearchQuery('')
    setSearchResults(null)
  }

  const handleCreate = async () => {
    // 如果已有空对话，直接切过去，不重复创建
    const existingEmpty = sessions.find(s => s.message_count === 0)
    if (existingEmpty) {
      navigate(`/chat/${existingEmpty.id}`)
      return
    }
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

  const handleRename = async (id: string, newTitle: string) => {
    await renameSession(id, newTitle)
  }

  const handleTogglePin = (id: string) => {
    setPinnedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [id, ...prev]
    )
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

  // 置顶的会话（排除空对话）
  const pinnedSessions = sessions.filter(s => pinnedIds.includes(s.id) && s.message_count > 0)
  // 未置顶的会话（排除空对话）
  const unpinnedSessions = sessions.filter(s => !pinnedIds.includes(s.id) && s.message_count > 0)

  // 按时间分组（未置顶的）
  const groupedSessions = {
    today: unpinnedSessions.filter(s => dayjs(s.updated_at).isSame(dayjs(), 'day')),
    yesterday: unpinnedSessions.filter(s => dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    week: unpinnedSessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day')) && !dayjs(s.updated_at).isSame(dayjs(), 'day') && !dayjs(s.updated_at).isSame(dayjs().subtract(1, 'day'), 'day')),
    month: unpinnedSessions.filter(s => dayjs(s.updated_at).isAfter(dayjs().subtract(30, 'day')) && !dayjs(s.updated_at).isAfter(dayjs().subtract(7, 'day'))),
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
        {searchOpen ? (
          <>
            <Button
              type="text"
              size="small"
              icon={<ArrowLeftOutlined />}
              onClick={handleCloseSearch}
              style={{ flexShrink: 0, marginRight: 8 }}
            />
            <Input
              placeholder="搜索对话..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              autoFocus
              style={{ flex: 1 }}
              size="small"
              allowClear
            />
          </>
        ) : (
          <>
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
            <div style={{ display: 'flex', gap: 4 }}>
              <Tooltip title="搜索">
                <Button
                  type="text"
                  size="small"
                  icon={<SearchOutlined />}
                  onClick={() => setSearchOpen(true)}
                  style={{ flexShrink: 0 }}
                />
              </Tooltip>
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
          </>
        )}
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

      {/* 搜索模式：显示搜索结果 */}
      {searchOpen ? (
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 8px' }}>
          {searching ? (
            <Spin size="small" style={{ display: 'block', margin: '24px auto' }} />
          ) : searchResults && searchResults.length === 0 ? (
            <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24, fontSize: 13 }}>
              未找到匹配的对话
            </Text>
          ) : searchResults && searchResults.length > 0 ? (
            searchResults.map((item: any) => (
              <div
                key={item.id}
                onClick={() => {
                  handleCloseSearch()
                  navigate(`/chat/${item.id}`)
                }}
                style={{
                  padding: '10px 12px',
                  marginBottom: 4,
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: sessionId === item.id ? '#e6f4ff' : 'transparent',
                  transition: 'background 0.2s',
                }}
              >
                <Text ellipsis style={{ fontSize: 13, fontWeight: 500 }}>
                  {item.title}
                </Text>
                {item.match_preview && (
                  <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                    ...{item.match_preview}...
                  </Text>
                )}
              </div>
            ))
          ) : null}
        </div>
      ) : (
        /* 正常模式：显示会话列表 */
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '0 8px',
          position: 'relative',
        }}>
          {/* 置顶组 */}
          {pinnedSessions.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>置顶</Text>
            <SessionList
              sessions={pinnedSessions}
              onDelete={handleDelete}
              onRename={handleRename}
              onTogglePin={handleTogglePin}
              pinnedIds={pinnedIds}
              onNavigate={navigate}
              sessionId={sessionId}
            />
          </>
        )}
        {/* 今天 */}
        {groupedSessions.today.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>今天</Text>
            <SessionList
              sessions={groupedSessions.today}
              onDelete={handleDelete}
              onRename={handleRename}
              onTogglePin={handleTogglePin}
              pinnedIds={pinnedIds}
              onNavigate={navigate}
              sessionId={sessionId}
            />
          </>
        )}
        {/* 昨天 */}
        {groupedSessions.yesterday.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>昨天</Text>
            <SessionList
              sessions={groupedSessions.yesterday}
              onDelete={handleDelete}
              onRename={handleRename}
              onTogglePin={handleTogglePin}
              pinnedIds={pinnedIds}
              onNavigate={navigate}
              sessionId={sessionId}
            />
          </>
        )}
        {/* 7 天内 */}
        {groupedSessions.week.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>7 天内</Text>
            <SessionList
              sessions={groupedSessions.week}
              onDelete={handleDelete}
              onRename={handleRename}
              onTogglePin={handleTogglePin}
              pinnedIds={pinnedIds}
              onNavigate={navigate}
              sessionId={sessionId}
            />
          </>
        )}
        {/* 30 天内 */}
        {groupedSessions.month.length > 0 && (
          <>
            <Text type="secondary" style={{ fontSize: 11, padding: '8px 8px 4px', display: 'block' }}>30 天内</Text>
            <SessionList
              sessions={groupedSessions.month}
              onDelete={handleDelete}
              onRename={handleRename}
              onTogglePin={handleTogglePin}
              pinnedIds={pinnedIds}
              onNavigate={navigate}
              sessionId={sessionId}
            />
          </>
        )}

        {/* 底部模糊渐变 */}
        <div style={{
          position: 'sticky',
          bottom: 0,
          height: 24,
          background: 'linear-gradient(to top, rgba(250, 250, 250, 1) 0%, rgba(250, 250, 250, 0) 100%)',
          pointerEvents: 'none',
        }} />
      </div>
      )}

      {/* 底部用户信息 - 可点击 */}
      {user && (
        <Dropdown
          menu={{
            items: userMenuItems,
            style: { width: 160, marginLeft: 8 },
          }}
          placement="topLeft"
          trigger={['click']}
        >
          <div style={{
            padding: '12px 16px',
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
function SessionList({ sessions, onDelete, onNavigate, onRename, onTogglePin, pinnedIds, sessionId }: {
  sessions: any[]
  onDelete: (id: string) => void
  onNavigate: (path: string) => void
  onRename: (id: string, newTitle: string) => void
  onTogglePin: (id: string) => void
  pinnedIds: string[]
  sessionId: string | undefined
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const handleStartRename = (id: string, title: string) => {
    setEditingId(id)
    setEditValue(title)
  }

  const handleConfirmRename = (id: string) => {
    if (editValue.trim()) {
      onRename(id, editValue.trim())
    }
    setEditingId(null)
    setEditValue('')
  }

  const handleCancelRename = () => {
    setEditingId(null)
    setEditValue('')
  }

  return (
    <div>
      {sessions.map((session) => {
        const isSelected = sessionId === session.id
        const isHovered = hoveredId === session.id
        const isEditing = editingId === session.id
        const isPinned = pinnedIds.includes(session.id)

        const menuItems: MenuProps['items'] = [
          {
            key: 'rename',
            icon: <EditOutlined />,
            label: '重命名',
            onClick: () => handleStartRename(session.id, session.title),
          },
          {
            key: 'share',
            icon: <ShareAltOutlined />,
            label: '分享',
            onClick: () => {
              message.info('分享功能开发中...')
            },
          },
          { type: 'divider' },
          {
            key: 'delete',
            icon: <DeleteOutlined />,
            label: '删除',
            danger: true,
            onClick: () => onDelete(session.id),
          },
        ]

        return (
          <div
            key={session.id}
            onClick={() => {
              if (!isEditing) onNavigate(`/chat/${session.id}`)
            }}
            onMouseEnter={() => setHoveredId(session.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              padding: '10px 12px',
              marginBottom: 2,
              borderRadius: 8,
              background: isSelected ? '#e6f4ff' : (isHovered ? '#f5f5f5' : 'transparent'),
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              transition: 'background 0.2s',
            }}
          >
            {/* 内联重命名 */}
            {isEditing ? (
              <div style={{ flex: 1, display: 'flex', gap: 4, alignItems: 'center' }}>
                <Input
                  size="small"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onPressEnter={() => handleConfirmRename(session.id)}
                  autoFocus
                  style={{ flex: 1, fontSize: 13 }}
                  onClick={(e) => e.stopPropagation()}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleConfirmRename(session.id)
                  }}
                  style={{ padding: 0, width: 20, height: 20 }}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCancelRename()
                  }}
                  style={{ padding: 0, width: 20, height: 20 }}
                />
              </div>
            ) : (
              <Text
                ellipsis={{ tooltip: session.title }}
                style={{
                  flex: 1,
                  fontSize: 13,
                  color: isSelected ? '#1677ff' : undefined,
                }}
              >
                {session.title}
              </Text>
            )}

            {/* 悬停时显示图标 */}
            {!isEditing && isHovered && (
              <div style={{ display: 'flex', gap: 4, marginLeft: 8, flexShrink: 0 }}>
                <Tooltip title={isPinned ? '取消置顶' : '置顶'}>
                  <Button
                    type="text"
                    size="small"
                    icon={<PushpinOutlined style={{ color: isPinned ? '#1677ff' : undefined }} />}
                    style={{ fontSize: 12, padding: 0, width: 20, height: 20 }}
                    onClick={(e) => {
                      e.stopPropagation()
                      onTogglePin(session.id)
                    }}
                  />
                </Tooltip>
                <Dropdown menu={{ items: menuItems }} trigger={['click']}>
                  <Button
                    type="text"
                    size="small"
                    icon={<MoreOutlined />}
                    style={{ fontSize: 14, padding: 0, width: 20, height: 20 }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Dropdown>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
