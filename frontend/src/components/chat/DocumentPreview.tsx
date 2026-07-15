import { useEffect, useState } from 'react'
import { Modal, Spin, Typography, Tag, Divider, Empty } from 'antd'
import { FileTextOutlined, FilePdfOutlined, FileExcelOutlined } from '@ant-design/icons'

const { Text, Title, Paragraph } = Typography

interface Chunk {
  page: number
  chunk_index: number
  content: string
}

interface PreviewData {
  doc_id: string
  filename: string
  file_type: string
  total_chunks: number
  highlight_page: number | null
  chunks: Chunk[]
}

interface Props {
  docId: string | null
  filename: string
  highlightPage?: number | null
  open: boolean
  onClose: () => void
}

const typeIcons: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#ff4d4f' }} />,
  docx: <FileTextOutlined style={{ color: '#1677ff' }} />,
  doc: <FileTextOutlined style={{ color: '#1677ff' }} />,
  xlsx: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  csv: <FileExcelOutlined style={{ color: '#52c41a' }} />,
}

export default function DocumentPreview({ docId, filename, highlightPage, open, onClose }: Props) {
  const [data, setData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!docId || !open) return
    setLoading(true)
    setError('')
    const url = `/api/docs/${docId}/preview` + (highlightPage ? `?page=${highlightPage}` : '')
    fetch(url, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error('加载失败')
        return res.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId, highlightPage, open])

  // 按页分组
  const pageGroups: Record<number, Chunk[]> = {}
  if (data?.chunks) {
    data.chunks.forEach((c) => {
      const p = c.page || 1
      if (!pageGroups[p]) pageGroups[p] = []
      pageGroups[p].push(c)
    })
  }
  const pages = Object.keys(pageGroups).map(Number).sort((a, b) => a - b)

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {data && (typeIcons[data.file_type] || <FileTextOutlined />)}
          <Text strong>{filename}</Text>
          {data && (
            <Tag>{data.total_chunks} 个片段 · {pages.length} 页</Tag>
          )}
        </div>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={null}
      style={{ top: 20 }}
    >
      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}
      {error && <Empty description={error} />}

      {data && (
        <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
          {pages.map((page) => (
            <div key={page} style={{ marginBottom: 16 }}>
              <Tag color={page === highlightPage ? 'red' : 'default'}>
                第 {page} 页
                {page === highlightPage && ' ★ 引用位置'}
              </Tag>
              {pageGroups[page].map((chunk) => (
                <Paragraph
                  key={chunk.chunk_index}
                  style={{
                    fontSize: 13,
                    lineHeight: 1.8,
                    padding: '8px 12px',
                    background: page === highlightPage ? '#fff7e6' : '#fafafa',
                    borderRadius: 6,
                    whiteSpace: 'pre-wrap',
                    margin: '4px 0',
                  }}
                >
                  {chunk.content}
                </Paragraph>
              ))}
              <Divider style={{ margin: '8px 0' }} />
            </div>
          ))}
        </div>
      )}
    </Modal>
  )
}
