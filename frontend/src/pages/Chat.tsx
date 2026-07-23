import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Input, Button, Typography, message, Skeleton, Tooltip, Dropdown } from 'antd'
import { SendOutlined, MenuUnfoldOutlined, SearchOutlined, PlusCircleOutlined, FilePdfOutlined, CopyOutlined, BulbOutlined, GlobalOutlined } from '@ant-design/icons'

/** 自定义分享图标（弯箭头向右） */
function ShareIcon(props: { style?: React.CSSProperties }) {
  return (
    <span role="img" className="anticon" style={props.style}>
      <svg viewBox="0 0 20 20" width="1em" height="1em" fill="currentColor">
        <path d="M9.73047 1.98239C9.73046 1.21153 10.6128 0.810523 11.1895 1.25486L11.3008 1.35544L18.3906 8.83005C18.8698 9.33527 18.8696 10.1273 18.3906 10.6328L11.3008 18.1152C10.735 18.7123 9.73046 18.3118 9.73047 17.4892V12.9765C9.05058 12.9603 8.23982 12.9642 7.26075 13.206C5.95079 13.5297 4.32474 14.294 2.49512 16.1133C2.27349 16.3334 1.96525 16.3697 1.72364 16.2793C1.47489 16.1859 1.24879 15.9363 1.25 15.5937L1.25879 15.167C1.33996 13.0226 1.97201 10.7003 3.34278 8.85642C4.71905 7.00534 6.81702 5.67342 9.73047 5.48728V1.98239ZM11.1504 6.15427C11.1502 6.57441 10.8056 6.88304 10.4209 6.88376C7.60432 6.88909 5.7029 8.06242 4.48243 9.70407C3.57516 10.9245 3.03042 12.426 2.79981 13.9394C4.29988 12.7446 5.69229 12.1304 6.91993 11.8271C8.47348 11.4433 9.75076 11.5693 10.4229 11.5713C10.8512 11.5725 11.1504 11.926 11.1504 12.3017V16.209L17.2881 9.73142L11.1504 3.25974V6.15427Z" />
      </svg>
    </span>
  )
}
import { useChatStore } from '../stores/chatStore'
import SessionSidebar from '../components/chat/SessionSidebar'
import MessageBubble from '../components/chat/MessageBubble'
import SearchModal from '../components/chat/SearchModal'

const { Text } = Typography

export default function Chat() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [searchParams] = useSearchParams()
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [searchMode, setSearchMode] = useState<'local' | 'web'>('local')
  const [deepThink, setDeepThink] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchModalOpen, setSearchModalOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [showScrollBottom, setShowScrollBottom] = useState(false)
  const lastScrolledMsg = useRef('')
  const userScrolledUp = useRef(false)  // 用户在流式输出中是否主动上滑

  // 高亮词和滚动目标从 URL 参数读取，用 state 确保渲染一致性
  const [highlightKeyword, setHighlightKeyword] = useState('')
  const [scrollTargetMsg, setScrollTargetMsg] = useState('')

  // URL 参数变化时同步到 state
  useEffect(() => {
    const hq = searchParams.get('hq') || ''
    const hm = searchParams.get('hm') || ''
    setHighlightKeyword(hq)
    setScrollTargetMsg(hm)
  }, [searchParams])

  const {
    currentSession,
    messages,
    streamingContent,
    streamingThinking,
    thinkingDone,
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
    const init = async () => {
      await fetchSessions()
      if (sessionId) {
        selectSession(sessionId)
        fetchMessages(sessionId)
      }
    }
    init()
  }, [sessionId])

  // 流式开始时重置上滑标记，流式结束后强制滚到底
  useEffect(() => {
    if (isStreaming) {
      userScrolledUp.current = false
    } else {
      // 流式结束，确保滚动到最底部（包括引用等全部内容）
      const container = scrollContainerRef.current
      if (container) {
        requestAnimationFrame(() => {
          container.scrollTop = container.scrollHeight
        })
      }
    }
  }, [isStreaming])

  useEffect(() => {
    if (!isStreaming) return
    const container = scrollContainerRef.current
    if (!container) return
    // 用户上滑过就不跟滚
    if (userScrolledUp.current) return
    requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight
    })
  }, [streamingContent, streamingThinking, isStreaming])

  // 搜索跳转滚动：找到匹配消息并滚动到高亮词位置
  useEffect(() => {
    if (messages.length === 0 || loading) return
    if (!highlightKeyword && !scrollTargetMsg) return
    // 防止同一搜索上下文中重复滚动
    const scrollKey = scrollTargetMsg || highlightKeyword
    if (lastScrolledMsg.current === scrollKey) return

    const tryScroll = () => {
      let target: HTMLElement | null = null

      // 1. 优先定位到精确匹配的消息 ID
      if (scrollTargetMsg) {
        const el = document.getElementById(`msg-${scrollTargetMsg}`)
        if (el) target = el.querySelector('.search-highlight') || el
      }

      // 2. 如果没有精确 ID（标题匹配），查找第一个包含关键词的消息
      if (!target && highlightKeyword) {
        for (const m of messages) {
          if (m.content.toLowerCase().includes(highlightKeyword.toLowerCase())) {
            const el = document.getElementById(`msg-${m.id}`)
            if (el) { target = el.querySelector('.search-highlight') || el; break }
          }
        }
      }

      // 3. 兜底：滚到第一条消息
      if (!target && messages.length > 0) {
        target = document.getElementById(`msg-${messages[0].id}`)
      }

      if (target) {
        lastScrolledMsg.current = scrollKey
        target.scrollIntoView({ block: 'center', behavior: 'smooth' })
      }
    }

    // 给 React 渲染 + rehype-raw 处理留时间
    setTimeout(tryScroll, 200)
  }, [scrollTargetMsg, highlightKeyword, messages, loading])

  // 切换会话或消息首次加载时直接定位到底部（useLayoutEffect 在绘制前执行，无闪烁）
  useLayoutEffect(() => {
    lastScrolledMsg.current = ''
    if (messages.length > 0 && !loading) {
      const el = scrollContainerRef.current
      if (el) {
        el.scrollTop = el.scrollHeight
      }
    }
  }, [sessionId, messages.length > 0 && !loading])

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
    sendMessage(targetSessionId, text, searchMode, deepThink)
      .catch(() => message.error('发送失败，请重试'))
      .finally(() => setSending(false))
  }

  const handleScroll = () => {
    const el = scrollContainerRef.current
    if (!el) return
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight
    setShowScrollBottom(dist > 200)
    // 跟踪用户上滑意图：距底 >80px 表示用户主动上滑
    if (isStreaming) {
      userScrolledUp.current = dist > 80
    }
  }

  const scrollToBottom = () => {
    const el = scrollContainerRef.current
    if (el) { el.scrollTop = el.scrollHeight; userScrolledUp.current = false }
  }

  const handleCreateSession = async (sendAfter?: string) => {
    try {
      await createSession()
      if (sendAfter) {
        const { currentSession: s } = useChatStore.getState()
        if (s) {
          setInputValue('')
          sendMessage(s.id, sendAfter, searchMode, deepThink)
        }
      }
    } catch {
      message.error('创建会话失败')
    }
  }

  // 分享 - 导出 PDF
  const handleExportPDF = () => {
    window.print()
  }

  // 分享 - 复制对话文本
  const handleCopyConversation = () => {
    const text = messages
      .map((m) => `${m.role === 'user' ? '👤 用户' : '🤖 AI'}\n${m.content}\n`)
      .join('\n---\n\n')
    navigator.clipboard.writeText(text).then(() => {
      message.success('对话已复制到剪贴板')
    }).catch(() => {
      message.error('复制失败')
    })
  }

  const shareMenuItems = {
    items: [
      { key: 'pdf', icon: <FilePdfOutlined />, label: '导出 PDF', onClick: handleExportPDF },
      { key: 'copy', icon: <CopyOutlined />, label: '复制对话文本', onClick: handleCopyConversation },
    ],
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#fff', position: 'relative', overflow: 'hidden' }}>
      <div className="no-print" style={{ position: 'absolute', top: 0, left: 0, height: '100%', zIndex: 10 }}>
        <SessionSidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          onSearch={() => setSearchModalOpen(true)}
        />
      </div>

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: '#fafafa',
        marginLeft: sidebarCollapsed ? 0 : 280,
        transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        {/* 折叠时有会话：浮动按钮 + 标题 + 分享 同一行 */}
        {sidebarCollapsed && currentSession && (
          <div className="no-print" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 24px 12px 16px', background: '#fafafa', flexShrink: 0, zIndex: 11, position: 'relative' }}>
            <Tooltip title="展开侧边栏">
              <Button type="text" icon={<MenuUnfoldOutlined />} onClick={() => setSidebarCollapsed(false)}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8, flexShrink: 0 }} />
            </Tooltip>
            <Tooltip title="搜索对话">
              <Button type="text" icon={<SearchOutlined />} onClick={() => setSearchModalOpen(true)}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8, flexShrink: 0 }} />
            </Tooltip>
            <Tooltip title="新建对话">
              <Button type="text" icon={<PlusCircleOutlined />} onClick={() => handleCreateSession()}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8, flexShrink: 0 }} />
            </Tooltip>
            <Text style={{ fontSize: 14, color: '#1f1f1f', flex: 1, marginLeft: 4 }}>{currentSession.title}</Text>
            {messages.length > 0 && (
              <Dropdown menu={shareMenuItems} trigger={['click']} placement="bottomRight">
                <Button type="text" icon={<ShareIcon />} />
              </Dropdown>
            )}
          </div>
        )}

        {/* 折叠时无会话：浮动按钮（绝对定位） */}
        {sidebarCollapsed && !currentSession && (
          <div className="no-print" style={{ position: 'absolute', top: 16, left: 16, zIndex: 100, display: 'flex', gap: 8 }}>
            <Tooltip title="展开侧边栏">
              <Button type="text" icon={<MenuUnfoldOutlined />} onClick={() => setSidebarCollapsed(false)}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8 }} />
            </Tooltip>
            <Tooltip title="搜索对话">
              <Button type="text" icon={<SearchOutlined />} onClick={() => setSearchModalOpen(true)}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8 }} />
            </Tooltip>
            <Tooltip title="新建对话">
              <Button type="text" icon={<PlusCircleOutlined />} onClick={() => handleCreateSession()}
                style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderRadius: 8 }} />
            </Tooltip>
          </div>
        )}

        {/* 打印时显示的标题 */}
        {currentSession && (
          <div className="print-only" style={{ display: 'none', textAlign: 'center', padding: '0 0 16px 0', borderBottom: '2px solid #e8e8e8', marginBottom: 16 }}>
            <Text strong style={{ fontSize: 18 }}>{currentSession.title}</Text>
          </div>
        )}

        {/* 展开时：正常标题栏 */}
        {currentSession && !sidebarCollapsed && (
          <div className="no-print" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', background: '#fafafa', flexShrink: 0 }}>
            <Text style={{ fontSize: 14, color: '#1f1f1f' }}>{currentSession.title}</Text>
            {messages.length > 0 && (
              <Dropdown menu={shareMenuItems} trigger={['click']} placement="bottomRight">
                <Button type="text" icon={<ShareIcon />} />
              </Dropdown>
            )}
          </div>
        )}

        <div ref={scrollContainerRef} onScroll={handleScroll} style={{ flex: 1, overflow: 'auto', padding: '0 24px 24px', background: '#fafafa' }}>
          {loading && messages.length === 0 && currentSession ? (
            <div style={{ maxWidth: 800, margin: '0 auto' }}>
              <Skeleton active avatar paragraph={{ rows: 3 }} />
            </div>
          ) : messages.length === 0 && !streamingContent ? (
            // 空会话：垂直居中欢迎页
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 20 }}>
              <Text style={{ fontSize: 18, color: '#999', fontWeight: 300 }}>有问题，随便问</Text>
              <div style={{ width: '100%', maxWidth: 680, position: 'relative' }}>
                <Input.TextArea
                  className="chat-input"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleCreateSession(inputValue.trim()) } }}
                  placeholder="输入你的问题，按 Enter 发送"
                  autoSize={{ minRows: 3, maxRows: 6 }}
                  style={{
                    width: '100%',
                    borderRadius: 16,
                    border: '1px solid #e0e0e0',
                    padding: '16px 52px 44px 16px',
                    fontSize: 15,
                    lineHeight: 1.6,
                    resize: 'none',
                    background: '#fff',
                  }}
                />
                <div style={{ position: 'absolute', bottom: 10, left: 16, display: 'flex', gap: 8 }}>
                  <Button size="small" type="default" icon={<BulbOutlined />}
                    onClick={() => setDeepThink(!deepThink)}
                    style={{ borderRadius: 16, fontSize: 14, padding: '4px 14px', height: 30, color: deepThink ? '#1677ff' : '#666', background: deepThink ? '#e6f4ff' : '#fff', border: deepThink ? '1px solid #91caff' : '1px solid #e8e8e8', boxShadow: 'none' }}
                  >深度思考</Button>
                  <Button size="small" type="default" icon={<GlobalOutlined />}
                    onClick={() => setSearchMode(searchMode === 'web' ? 'local' : 'web')}
                    style={{ borderRadius: 16, fontSize: 14, padding: '4px 14px', height: 30, color: searchMode === 'web' ? '#1677ff' : '#666', background: searchMode === 'web' ? '#e6f4ff' : '#fff', border: searchMode === 'web' ? '1px solid #91caff' : '1px solid #e8e8e8', boxShadow: 'none' }}
                  >联网搜索</Button>
                </div>
                <Button type="primary" shape="circle" icon={<SendOutlined />}
                  onClick={() => handleCreateSession(inputValue.trim())}
                  disabled={!inputValue.trim()}
                  style={{ position: 'absolute', bottom: 10, right: 16, width: 34, height: 34 }}
                />
              </div>
            </div>
          ) : (
            <div className="print-area" style={{ maxWidth: 800, margin: '0 auto' }}>
              {messages.map((msg) => (
                <div key={msg.id} id={`msg-${msg.id}`}>
                  <MessageBubble message={msg} highlight={highlightKeyword || undefined} />
                </div>
              ))}
              {isStreaming && (
                <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center', padding: '8px 16px' }}>
                  <div style={{ width: 8, height: 8, background: streamingContent ? '#52c41a' : '#1677ff', borderRadius: '50%' }} />
                  <span style={{ color: '#888', fontSize: 13 }}>
                    {statusText || (streamingContent ? '正在生成回答...' : '正在处理...')}
                  </span>
                </div>
              )}
              {(streamingContent || streamingThinking) && (
                <MessageBubble message={{ id: 'streaming', role: 'assistant', content: streamingContent, thinking: streamingThinking || null, thinkingTime: null, citations: null, created_at: '' }} isStreaming thinkingDone={thinkingDone} />
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 有消息时显示底部输入框 */}
        {currentSession && messages.length > 0 && (
        <div className="no-print" style={{ padding: '0 24px 5px' }}>
          {showScrollBottom && (
            <div style={{ maxWidth: 800, margin: '0 auto 12px auto', display: 'flex', justifyContent: 'flex-end' }}>
              <Button shape="circle"
                icon={<svg viewBox="0 0 14 14" width="14" height="14" fill="currentColor"><path d="M11.8486 5.5L11.4238 5.92383L8.69727 8.65137C8.44157 8.90706 8.21562 9.13382 8.01172 9.29785C7.79912 9.46883 7.55595 9.61756 7.25 9.66602C7.08435 9.69222 6.91565 9.69222 6.75 9.66602C6.44405 9.61756 6.20088 9.46883 5.98828 9.29785C5.78438 9.13382 5.55843 8.90706 5.30273 8.65137L2.57617 5.92383L2.15137 5.5L3 4.65137L3.42383 5.07617L6.15137 7.80273C6.42595 8.07732 6.59876 8.24849 6.74023 8.3623C6.87291 8.46904 6.92272 8.47813 6.9375 8.48047C6.97895 8.48703 7.02105 8.48703 7.0625 8.48047C7.07728 8.47813 7.12709 8.46904 7.25977 8.3623C7.40124 8.24849 7.57405 8.07732 7.84863 7.80273L10.5762 5.07617L11 4.65137L11.8486 5.5Z" /></svg>}
                onClick={scrollToBottom}
                style={{ width: 36, height: 36, boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }}
              />
            </div>
          )}
          <div style={{ maxWidth: 800, margin: '0 auto', position: 'relative' }}>
            <Input.TextArea className="chat-input" value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder={isStreaming ? "AI 回复中..." : "输入你的问题，按 Enter 发送"}
              autoSize={{ minRows: 4, maxRows: 8 }}
              style={{ width: '100%', borderRadius: 16, border: '1px solid #e0e0e0', padding: '16px 52px 44px 16px', fontSize: 15, lineHeight: 1.6, resize: 'none', background: '#fff' }}
            />
            <div style={{ position: 'absolute', bottom: 10, left: 16, display: 'flex', gap: 8 }}>
              <Button size="small" type="default" icon={<BulbOutlined />} onClick={() => setDeepThink(!deepThink)}
                style={{ borderRadius: 16, fontSize: 14, padding: '4px 14px', height: 30, color: deepThink ? '#1677ff' : '#666', background: deepThink ? '#e6f4ff' : '#fff', border: deepThink ? '1px solid #91caff' : '1px solid #e8e8e8', boxShadow: 'none' }}
              >深度思考</Button>
              <Button size="small" type="default" icon={<GlobalOutlined />} onClick={() => setSearchMode(searchMode === 'web' ? 'local' : 'web')}
                style={{ borderRadius: 16, fontSize: 14, padding: '4px 14px', height: 30, color: searchMode === 'web' ? '#1677ff' : '#666', background: searchMode === 'web' ? '#e6f4ff' : '#fff', border: searchMode === 'web' ? '1px solid #91caff' : '1px solid #e8e8e8', boxShadow: 'none' }}
              >联网搜索</Button>
            </div>
            <Button type="primary" shape="circle" icon={<SendOutlined />} onClick={handleSend}
              loading={sending} disabled={!inputValue.trim()}
              style={{ position: 'absolute', bottom: 10, right: 16, width: 34, height: 34 }} />
          </div>
          {messages.length > 0 && (
            <Text type="secondary" style={{ fontSize: 11, display: 'block', textAlign: 'center', marginTop: 5, marginBottom: 5 }}>
              内容由 AI 生成，请仔细甄别
            </Text>
          )}
        </div>
        )}
      </div>

      <SearchModal open={searchModalOpen} onClose={() => setSearchModalOpen(false)} />
    </div>
  )
}
