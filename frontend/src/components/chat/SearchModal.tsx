import { useState, useEffect, useRef } from 'react'
import { Input, Typography, Spin, Empty } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { chatAPI } from '../../api/chat'

const { Text } = Typography

/** 高亮关键词 */
function highlighter(text: string, keyword: string): React.ReactNode {
  if (!keyword || !text) return text
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, i) => {
    if (!part) return null
    if (part.toLowerCase() === keyword.toLowerCase()) {
      return (
        <span key={i} style={{ background: '#FFD700', color: '#000', fontWeight: 600, borderRadius: 2, padding: '1px 2px' }}>
          {part}
        </span>
      )
    }
    return part
  })
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function SearchModal({ open, onClose }: Props) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const inputRef = useRef<any>(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setResults([])
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  const handleSearch = async (q: string) => {
    setQuery(q)
    if (!q.trim()) {
      setResults([])
      return
    }
    setSearching(true)
    try {
      const res = await chatAPI.searchSessions(q.trim())
      setResults(res.data.items || [])
    } catch {
      setResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleSelect = (sessionId: string, messageId?: string) => {
    onClose()
    const params = new URLSearchParams()
    params.set('hq', query)
    if (messageId) params.set('hm', messageId)
    navigate(`/chat/${sessionId}?${params.toString()}`)
  }

  if (!open) return null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(0, 0, 0, 0.3)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        justifyContent: 'center',
        paddingTop: '12vh',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 560,
          maxHeight: '70vh',
          background: '#fff',
          borderRadius: 12,
          boxShadow: '0 8px 40px rgba(0, 0, 0, 0.15)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 搜索输入 */}
        <div style={{
          padding: '16px 20px',
          borderBottom: results.length > 0 ? '1px solid #f0f0f0' : 'none',
        }}>
          <Input
            ref={inputRef}
            prefix={<SearchOutlined style={{ color: '#999' }} />}
            placeholder="搜索对话..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            size="large"
            bordered={false}
            style={{ fontSize: 16 }}
          />
        </div>

        {/* 搜索结果 */}
        <div style={{ flex: 1, overflow: 'auto', padding: results.length > 0 ? '8px 12px' : 0 }}>
          {searching ? (
            <Spin size="small" style={{ display: 'block', margin: '40px auto' }} />
          ) : query && results.length === 0 ? (
            <Empty
              description="未找到匹配的对话"
              style={{ padding: '40px 0' }}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            results.map((item: any) => (
              <div
                key={item.id}
                onClick={() => handleSelect(item.id, item.match_message_id)}
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Text strong style={{ fontSize: 14 }}>{highlighter(item.title, query)}</Text>
                {item.match_preview && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      ...{highlighter(item.match_preview, query)}...
                    </Text>
                  </div>
                )}
                <div style={{ marginTop: 2 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {item.message_count} 条消息
                  </Text>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
