import { useState } from 'react'
import { Tag, Typography, Tooltip } from 'antd'
import { FileTextOutlined, EyeOutlined } from '@ant-design/icons'
import DocumentPreview from './DocumentPreview'

const { Text } = Typography

interface Props {
  citation: {
    source: string
    doc_id?: string
    pages?: number[] | null
  }
  index: number
}

export default function CitationCard({ citation, index }: Props) {
  const [previewOpen, setPreviewOpen] = useState(false)
  const pages = citation.pages
  const docId = citation.doc_id
  const fileName = citation.source

  return (
    <>
      <div
        onClick={() => docId && setPreviewOpen(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '5px 8px',
          fontSize: 12,
          cursor: docId ? 'pointer' : 'default',
          borderRadius: 6,
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => {
          if (docId) e.currentTarget.style.background = '#e6f4ff'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent'
        }}
      >
        <Tag color="blue" style={{ margin: 0 }}>[{index}]</Tag>
        <FileTextOutlined style={{ color: '#999' }} />
        <Tooltip title={docId ? '点击预览文档内容' : ''}>
          <Text style={{ fontSize: 12, color: docId ? '#1677ff' : undefined }}>
            {fileName}
          </Text>
        </Tooltip>
        {pages && pages.length > 0 && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            第 {pages.join(', ')} 页
          </Text>
        )}
        {docId && <EyeOutlined style={{ color: '#1677ff', fontSize: 10 }} />}
      </div>

      {docId && (
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
