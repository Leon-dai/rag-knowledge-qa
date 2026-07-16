import { Avatar, Typography, Space } from 'antd'
import { UserOutlined, RobotOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import CitationCard from './CitationCard'

const { Text } = Typography

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: any[] | null
  created_at: string
}

interface Props {
  message: Message
  isStreaming?: boolean
}

export default function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user'

  if (isUser) {
    // 用户消息：蓝色气泡，右对齐
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
          <Text style={{ whiteSpace: 'pre-wrap' }}>{message.content}</Text>
        </div>
      </div>
    )
  }

  // AI 回复：无气泡，纯文本 + 头像，左对齐（ChatGPT 风格）
  return (
    <div style={{
      display: 'flex',
      gap: 12,
      marginBottom: 24,
      alignItems: 'flex-start',
    }}>
      <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a', flexShrink: 0 }} />
      <div style={{ flex: 1, maxWidth: '85%' }}>
        <div className="markdown-content" style={{ lineHeight: 1.8, fontSize: 14 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
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
