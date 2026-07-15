import { useState } from 'react'
import { Tag, Typography, Tooltip } from 'antd'
import { FileTextOutlined, EyeOutlined, GlobalOutlined } from '@ant-design/icons'
import DocumentPreview from './DocumentPreview'

const { Text } = Typography

interface Props {
  citation: {
    source: string
    doc_id?: string
    pages?: number[] | null
    url?: string
  }
  index: number
}

export default function CitationCard({ citation, index }: Props) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const pages = citation.pages
  const docId = citation.doc_id
  const url = citation.url
  const isWebSource = docId?.startsWith('web_') || !!url
  const fileName = citation.source

  const handleClick = () => {
    if (isWebSource && url) {
      // 网络来源：打开外部链接
      window.open(url, '_blank')
    } else if (docId) {
      // 本地来源：预览文档
      setPreviewOpen(true)
    }
  }

  return (
    <>
      <div
        onClick={handleClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 8px',
          fontSize: 12,
          cursor: (docId || url) ? 'pointer' : 'default',
          borderRadius: 6,
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (docId || url) e.currentTarget.style.background = isWebSource ? '#f6ffed' : '#e6f4ff'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
      >
        <Tag color={isWebSource ? 'green' : 'blue'} style={{ margin: 0 }}>[{index}]</Tag>
        {isWebSource ? (
          <GlobalOutlined style={{ color: '#52c41a' }} />
        ) : (
          <FileTextOutlined style={{ color: '#999' }} />
        )}
        <Tooltip title={
          isWebSource ? '点击打开外部链接' :
          docId ? '点击预览文档内容' : ''
        }>
          <Text style={{ fontSize: 12, color: isWebSource ? '#52c41a' : (docId ? '#1677ff' : undefined) }}>
            {isWebSource ? fileName.replace('🌐 ', '') : fileName}
          </Text>
        </Tooltip>
        {pages && pages.length > 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            第 {pages.join(', ')} 页
          </Text>
        )}
        {(docId || url) && (
          isWebSource ? (
            <GlobalOutlined style={{ color: '#52c41a', fontSize: 10 }} />
          ) : (
            <EyeOutlined style={{ color: '#1677ff', fontSize: 10 }} />
          )
        )}
      </div>

      {docId && !isWebSource && (
        <DocumentPreview
          docId={docId}
          filename={fileName}
          highlightPage={pages?.[0] ?? null}
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </>
  )
}
