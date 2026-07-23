import { useEffect, useState } from 'react'
import {
  Card, Table, Button, Upload, Space, Tag, Popconfirm, message,
  Typography, Modal, Progress
} from 'antd'
import {
  UploadOutlined, DeleteOutlined, ReloadOutlined, DownloadOutlined,
  FilePdfOutlined, FileTextOutlined, FileExcelOutlined,
  FileOutlined, LoadingOutlined, SyncOutlined
} from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { useKBStore } from '../../stores/kbStore'
import { docsAPI } from '../../api/docs'
import dayjs from 'dayjs'

const { Title } = Typography

const fileTypeIcon: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#ff4d4f' }} />,
  docx: <FileTextOutlined style={{ color: '#1677ff' }} />,
  doc: <FileTextOutlined style={{ color: '#1677ff' }} />,
  txt: <FileTextOutlined />,
  md: <FileTextOutlined />,
  csv: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  xlsx: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  xls: <FileExcelOutlined style={{ color: '#52c41a' }} />,
}

const statusTag: Record<string, { color: string; text: string }> = {
  uploaded: { color: 'default', text: '待处理' },
  processing: { color: 'processing', text: '处理中' },
  ready: { color: 'success', text: '就绪' },
  error: { color: 'error', text: '失败' },
}

export default function DocumentList() {
  const { documents, total, page, loading, fetchDocuments, uploadDocument, deleteDocument, reprocessDocument } = useKBStore()
  const [uploading, setUploading] = useState(false)
  const [detailModal, setDetailModal] = useState<string | null>(null)

  const hasProcessing = documents.some((d: any) => d.status === 'processing' || d.status === 'uploaded')

  useEffect(() => {
    fetchDocuments()
    // 有处理中的文档时每2秒刷新，否则每10秒
    const interval = hasProcessing ? 2000 : 10000
    const timer = setInterval(() => fetchDocuments(page), interval)
    return () => clearInterval(timer)
  }, [fetchDocuments, page, hasProcessing])

  const uploadProps: UploadProps = {
    accept: '.pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls',
    showUploadList: false,
    beforeUpload: async (file) => {
      setUploading(true)
      try {
        await uploadDocument(file)
        message.success(`"${file.name}" 上传成功`)
      } catch (err: any) {
        const detail = err?.response?.data?.detail
        message.error(typeof detail === 'string' ? detail : '上传失败')
      } finally {
        setUploading(false)
      }
      return false
    },
  }

  const columns = [
    {
      title: '文件名',
      dataIndex: 'original_filename',
      key: 'filename',
      render: (text: string, record: any) => (
        <Space>
          {fileTypeIcon[record.file_type] || <FileOutlined />}
          <a onClick={() => setDetailModal(record.id)}>{text}</a>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'type',
      width: 80,
      render: (t: string) => <Tag>{t.toUpperCase()}</Tag>,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'size',
      width: 100,
      render: (s: number) => s > 1024 * 1024
        ? `${(s / 1024 / 1024).toFixed(1)} MB`
        : `${(s / 1024).toFixed(1)} KB`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const st = statusTag[s] || { color: 'default', text: s }
        return (
          <Tag color={st.color} icon={s === 'processing' ? <SyncOutlined spin /> : undefined}>
            {st.text}
          </Tag>
        )
      },
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunks',
      width: 80,
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created',
      width: 160,
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: any) => (
        <Space size={0}>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => docsAPI.download(record.id, record.original_filename)}
          />
          {record.status === 'error' && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => reprocessDocument(record.id)}
            >
              重试
            </Button>
          )}
          <Popconfirm
            title="确定删除此文档？将同时删除对应的向量数据。"
            onConfirm={() => deleteDocument(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>知识库管理</Title>
        <Upload {...uploadProps}>
          <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
            上传文档
          </Button>
        </Upload>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 10,
            onChange: (p) => fetchDocuments(p),
            showTotal: (t) => `共 ${t} 篇文档`,
          }}
        />
      </Card>
    </div>
  )
}
