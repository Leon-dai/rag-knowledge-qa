import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Input, Button, Spin, Empty, Typography, message, Skeleton, Select, Tooltip } from 'antd'
import { SendOutlined, PlusOutlined, GlobalOutlined, DatabaseOutlined, MergeCellsOutlined } from '@ant-design/icons'
import { useChatStore } from '../stores/chatStore'
import SessionSidebar from '../components/chat/SessionSidebar'
import MessageBubble from '../components/chat/MessageBubble'

const { Text } = Typography
const { Option } = Select

export default function Chat() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [searchMode, setSearchMode] = useState<'local' | 'web' | 'mixed'>('local')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    sessions,
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

  // 流式输出时，内容满了就钉在底部，新内容自然往上推
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
      // 自动创建新会话
      await createSession()
      const { currentSession: newSession } = useChatStore.getState()
      targetSessionId = newSession?.id
      if (!targetSessionId) {
        message.error('创建会话失败')
        return
      }
    }

    // 立即清空输入框，不等待响应
    setInputValue('')
    // 只锁按钮一瞬间，流式响应由 store 管理
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
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      {/* 会话侧边栏 */}
      <SessionSidebar />

      {/* 聊天主区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
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
                  新建对话
                </Button>
              </Empty>
            </div>
          ) : (
            <div style={{ maxWidth: 800, margin: '0 auto' }}>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {/* 管道状态显示（呼吸灯 + 动态文字） */}
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
                    transition: 'color 0.3s',
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
          padding: '16px 24px',
          background: '#fff',
          borderTop: '1px solid #f0f0f0',
        }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            {/* 搜索模式选择器 */}
            <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text type="secondary" style={{ fontSize: 13 }}>搜索模式：</Text>
              <Select
                value={searchMode}
                onChange={setSearchMode}
                size="small"
                style={{ width: 180 }}
              >
                <Option value="local">
                  <DatabaseOutlined /> 本地知识库
                </Option>
                <Option value="web">
                  <GlobalOutlined /> 仅联网搜索
                </Option>
                <Option value="mixed">
                  <MergeCellsOutlined /> 混合搜索（推荐）
                </Option>
              </Select>
              <Tooltip title="本地：仅搜索上传的文档；联网：仅搜索互联网；混合：同时搜索本地和联网">
                <Text type="secondary" style={{ fontSize: 12 }}>ⓘ</Text>
              </Tooltip>
            </div>

            {/* 输入框和发送按钮 */}
            <div style={{ display: 'flex', gap: 12 }}>
              <Input.TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault()
                    handleSend()
                  }
                }}
                placeholder={isStreaming ? "AI 回复中，可直接输入新消息中断当前回复..." : "输入你的问题，按 Enter 发送，Shift+Enter 换行"}
                autoSize={{ minRows: 1, maxRows: 5 }}
                style={{ flex: 1 }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={sending}
                disabled={!inputValue.trim()}
              >
                发送
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
