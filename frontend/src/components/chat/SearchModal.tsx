import { useState, useEffect, useRef } from 'react'
import { Input, Typography, Spin, Empty } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { chatAPI } from '../../api/chat'

const { Text } = Typography

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

  const handleSelect = (sessionId: string) => {
    onClose()
    navigate(`/chat/${sessionId}`)
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
                onClick={() => handleSelect(item.id)}
                style={{
                  padding: '12px 16px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Text strong style={{ fontSize: 14 }}>{item.title}</Text>
                {item.match_preview && (
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      ...{item.match_preview}...
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