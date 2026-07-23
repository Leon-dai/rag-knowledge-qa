import { useMemo, useState } from 'react'
import { Avatar, Typography, Space } from 'antd'
import { UserOutlined, RobotOutlined, CaretDownOutlined, CaretRightOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import CitationCard from './CitationCard'

const { Text } = Typography

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking: string | null
  thinkingTime: number | null
  citations: any[] | null
  created_at: string
}

interface Props {
  message: Message
  isStreaming?: boolean
  highlight?: string
  thinkingDone?: boolean
}

const HIGHLIGHT_STYLE = 'background:#FFD700;color:#000;font-weight:600;border-radius:2px;padding:1px 3px;'

/** 在文本中高亮关键词，返回 React 节点（用于非 markdown 的文本） */
function highlightText(text: string, keyword: string): React.ReactNode {
  if (!keyword) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, i) => {
    if (!part) return null
    if (part.toLowerCase() === keyword.toLowerCase()) {
      return <span key={i} className="search-highlight" style={{ background: '#FFD700', color: '#000', fontWeight: 600, borderRadius: 2, padding: '1px 3px' }}>{part}</span>
    }
    return part
  })
}

/** 在 HTML/markdown 文本中嵌入高亮 span（用于 ReactMarkdown + rehype-raw） */
function highlightInHtml(text: string, keyword: string): string {
  if (!keyword) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(
    new RegExp(`(${escaped})`, 'gi'),
    `<span class="search-highlight" style="${HIGHLIGHT_STYLE}">$1</span>`
  )
}

export default function MessageBubble({ message, isStreaming, highlight, thinkingDone }: Props) {
  const isUser = message.role === 'user'
  const [thinkingExpanded, setThinkingExpanded] = useState(true)

  // AI 消息：预处理 markdown，在渲染前嵌入高亮 span
  const aiContent = useMemo(() => {
    if (!highlight) return message.content
    return highlightInHtml(message.content, highlight)
  }, [message.content, highlight])

  if (isUser) {
    return (
      <div style={{
        display: 'flex',
        gap: 12,
        marginBottom: 24,
        flexDirection: 'row-reverse',
      }}>
        <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1677ff', flexShrink: 0 }} />
        <div style={{
          maxWidth: '70%',
          background: '#e6f4ff',
          borderRadius: '12px 12px 4px 12px',
          padding: '10px 16px',
        }}>
          <Text style={{ whiteSpace: 'pre-wrap' }}>{highlight ? highlightText(message.content, highlight) : message.content}</Text>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex',
      gap: 12,
      marginBottom: 24,
      alignItems: 'flex-start',
    }}>
      <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a', flexShrink: 0 }} />
      <div style={{ flex: 1, maxWidth: '85%' }}>
        {/* 深度思考：可折叠区域 */}
        {message.thinking && (
          <div style={{ marginBottom: 12 }}>
            <div
              onClick={() => setThinkingExpanded(!thinkingExpanded)}
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 13,
                color: '#8c8c8c',
                marginBottom: 6,
                userSelect: 'none',
              }}
            >
              {thinkingExpanded ? <CaretDownOutlined /> : <CaretRightOutlined />}
              <span>
                {isStreaming && !thinkingDone
                  ? '思考中...'
                  : `已深度思考${message.thinkingTime ? ` (${message.thinkingTime}s)` : ''}`}
              </span>
            </div>
            {thinkingExpanded && (
              <div style={{
                padding: '0 0 0 14px',
                fontSize: 13,
                color: '#8c8c8c',
                lineHeight: 1.7,
                borderLeft: '3px solid #d9d9d9',
                whiteSpace: 'pre-wrap',
              }}>
                {message.thinking || ''}
              </div>
            )}
          </div>
        )}
        <div className="markdown-content" style={{ lineHeight: 1.8, fontSize: 14 }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={highlight ? [rehypeRaw] : undefined}
          >
            {aiContent}
          </ReactMarkdown>
        </div>

        {/* 引用来源 */}
        {message.citations && message.citations.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>📖 引用来源：</Text>
            <Space direction="vertical" style={{ width: '100%', marginTop: 4 }}>
              {message.citations.map((citation: any, idx: number) => (
                <CitationCard key={idx} citation={citation} index={idx + 1} />
              ))}
            </Space>
          </div>
        )}
      </div>
    </div>
  )
}
