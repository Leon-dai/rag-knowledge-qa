import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Input, Button, Empty, Typography, message, Skeleton, Tooltip } from 'antd'
import { SendOutlined, PlusOutlined, GlobalOutlined, DatabaseOutlined, MergeCellsOutlined, MenuUnfoldOutlined, SearchOutlined, PlusCircleOutlined } from '@ant-design/icons'
import { useChatStore } from '../stores/chatStore'
import SessionSidebar from '../components/chat/SessionSidebar'
import MessageBubble from '../components/chat/MessageBubble'
import SearchModal from '../components/chat/SearchModal'

const { Text } = Typography

// 搜索模式按钮配置
const SEARCH_MODES = [
  { value: 'local', label: '知识库', icon: <DatabaseOutlined />, tooltip: '仅搜索上传的文档' },
  { value: 'mixed', label: '智能搜索', icon: <MergeCellsOutlined />, tooltip: '同时搜索知识库和互联网（推荐）' },
  { value: 'web', label: '联网搜索', icon: <GlobalOutlined />, tooltip: '仅搜索互联网' },
]

export default function Chat() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [searchMode, setSearchMode] = useState<'local' | 'web' | 'mixed'>('mixed')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchModalOpen, setSearchModalOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    currentSession,
    messages,
    streamingContent,
    isStreaming,
    statusText,
    loading,
    fetchSessions,
    createSession,
    selectSession,
    fetchMessages,
    sendMessage,
  } = useChatStore()

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    if (sessionId) {
      selectSession(sessionId)
      fetchMessages(sessionId)
    }
  }, [sessionId, selectSession, fetchMessages])

  useEffect(() => {
    if (!isStreaming) return
    const el = messagesEndRef.current
    if (!el) return
    requestAnimationFrame(() => {
      el.scrollIntoView({ block: 'end', behavior: 'auto' })
    })
  }, [streamingContent, isStreaming])

  const handleSend = async () => {
    const text = inputValue.trim()
    if (!text || sending) return

    let targetSessionId = currentSession?.id

    if (!targetSessionId) {
      await createSession()
      const { currentSession: newSession } = useChatStore.getState()
      targetSessionId = newSession?.id
      if (!targetSessionId) {
        message.error('创建会话失败')
        return
      }
    }

    setInputValue('')
    setSending(true)
    sendMessage(targetSessionId, text, searchMode)
      .catch(() => message.error('发送失败，请重试'))
      .finally(() => setSending(false))
  }

  const handleCreateSession = async () => {
    try {
      await createSession()
    } catch {
      message.error('创建会话失败')
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#fff', position: 'relative', overflow: 'hidden' }}>
      {/* 会话侧边栏 - 用绝对定位实现滑入滑出动画 */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: '100%',
        zIndex: 10,
      }}>
        <SessionSidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          onSearch={() => setSearchModalOpen(true)}
        />
      </div>

      {/* 聊天主区域 */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
        marginLeft: sidebarCollapsed ? 0 : 280,
        transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        {/* 折叠后的浮动按钮 - 类似 DeepSeek */}
        {sidebarCollapsed && (
          <div style={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 100,
            display: 'flex',
            gap: 8,
          }}>
            <Tooltip title="展开侧边栏">
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setSidebarCollapsed(false)}
                style={{
                  width: 36,
                  height: 36,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  borderRadius: 8,
                }}
              />
            </Tooltip>
            <Tooltip title="搜索对话">
              <Button
                type="text"
                icon={<SearchOutlined />}
                onClick={() => setSearchModalOpen(true)}
                style={{
                  width: 36,
                  height: 36,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  borderRadius: 8,
                }}
              />
            </Tooltip>
            <Tooltip title="新建对话">
              <Button
                type="text"
                icon={<PlusCircleOutlined />}
                onClick={handleCreateSession}
                style={{
                  width: 36,
                  height: 36,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#fff',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  borderRadius: 8,
                }}
              />
            </Tooltip>
          </div>
        )}

        {/* 对话标题 */}
        {currentSession && (
          <div style={{
            textAlign: 'center',
            padding: '16px 24px 8px',
            background: '#fff',
          }}>
            <Text style={{ fontSize: 16, fontWeight: 500 }}>
              {currentSession.title}
            </Text>
          </div>
        )}

        {/* 消息列表 */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '24px',
          background: '#fafafa',
        }}>
          {loading ? (
            <div style={{ maxWidth: 800, margin: '0 auto' }}>
              <Skeleton active avatar paragraph={{ rows: 3 }} />
            </div>
          ) : messages.length === 0 && !streamingContent ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}>
              <Empty description="开始提问吧">
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateSession}>
                  开启新对话
                </Button>
              </Empty>
            </div>
          ) : (
            <div style={{ maxWidth: 800, margin: '0 auto' }}>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isStreaming && (
                <div style={{
                  display: 'flex',
                  gap: 12,
                  marginBottom: 24,
                  alignItems: 'center',
                  padding: '8px 16px',
                  opacity: streamingContent ? 0.5 : 1,
                  transition: 'opacity 0.3s',
                }}>
                  <div style={{
                    width: 8, height: 8,
                    background: streamingContent ? '#52c41a' : '#1677ff',
                    borderRadius: '50%',
                    animation: streamingContent ? 'none' : 'pulse 1s infinite',
                  }} />
                  <span style={{
                    color: '#888',
                    fontSize: 13,
                  }}>
                    {statusText || (streamingContent ? '正在生成回答...' : '正在处理...')}
                  </span>
                </div>
              )}
              {streamingContent && (
                <MessageBubble
                  message={{
                    id: 'streaming',
                    role: 'assistant',
                    content: streamingContent,
                    citations: null,
                    created_at: '',
                  }}
                  isStreaming
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div style={{
          padding: '16px 24px 24px',
          background: '#fff',
        }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            {/* 搜索模式按钮 */}
            <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
              {SEARCH_MODES.map((mode) => (
                <Tooltip key={mode.value} title={mode.tooltip}>
                  <Button
                    type={searchMode === mode.value ? 'primary' : 'default'}
                    size="small"
                    icon={mode.icon}
                    onClick={() => setSearchMode(mode.value as 'local' | 'web' | 'mixed')}
                    style={{ borderRadius: 20 }}
                  >
                    {mode.label}
                  </Button>
                </Tooltip>
              ))}
            </div>

            {/* 输入框 */}
            <div style={{
              background: '#f5f5f5',
              padding: '12px 16px',
              borderRadius: 12,
              border: '1px solid #e8e8e8',
              transition: 'border-color 0.3s',
            }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
                <Input.TextArea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder={isStreaming ? "AI 回复中..." : "输入你的问题，按 Enter 发送"}
                  autoSize={{ minRows: 1, maxRows: 5 }}
                  style={{
                    flex: 1,
                    border: 'none',
                    background: 'transparent',
                    boxShadow: 'none',
                    resize: 'none',
                  }}
                />
                <Button
                  type="primary"
                  shape="circle"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={sending}
                  disabled={!inputValue.trim()}
                  style={{
                    width: 36,
                    height: 36,
                    flexShrink: 0,
                  }}
                />
              </div>
            </div>

            {/* 底部提示 */}
            <Text type="secondary" style={{ fontSize: 11, display: 'block', textAlign: 'center', marginTop: 8 }}>
              内容由 AI 生成，请仔细甄别
            </Text>
          </div>
        </div>
      </div>

      {/* 搜索弹窗 */}
      <SearchModal
        open={searchModalOpen}
        onClose={() => setSearchModalOpen(false)}
      />
    </div>
  )
}