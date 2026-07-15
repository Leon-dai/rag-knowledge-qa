import { useEffect, useState } from 'react'
import { Card, Select, Button, Typography, message, Alert, Space, Tag, Divider, Spin } from 'antd'
import { SwapOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { adminAPI } from '../../api/admin'

const { Title, Text, Paragraph } = Typography

interface ModelOption {
  value: string
  label: string
  desc: string
}

interface ModelsData {
  llm: { options: ModelOption[]; current: string }
  embedding: { options: ModelOption[]; current: string }
  embedding_mismatch: {
    compatible: boolean
    stored: string | null
    current: string
    warning: string
  } | null
}

export default function ModelSettings() {
  const [data, setData] = useState<ModelsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [switchingLLM, setSwitchingLLM] = useState(false)
  const [switchingEmb, setSwitchingEmb] = useState(false)

  const fetchModels = () => {
    setLoading(true)
    adminAPI.getModels()
      .then((res) => setData(res.data))
      .catch(() => message.error('获取模型配置失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchModels() }, [])

  const handleSwitchLLM = async (model: string) => {
    setSwitchingLLM(true)
    try {
      const res = await adminAPI.switchLLM(model)
      message.success(res.data.message)
      fetchModels()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '切换失败')
    } finally {
      setSwitchingLLM(false)
    }
  }

  const handleSwitchEmb = async (model: string) => {
    setSwitchingEmb(true)
    try {
      const res = await adminAPI.switchEmbedding(model)
      message.warning(res.data.warning || res.data.message)
      fetchModels()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '切换失败')
    } finally {
      setSwitchingEmb(false)
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>模型设置</Title>

      {/* Embedding 模型不匹配警告 */}
      {data?.embedding_mismatch && !data.embedding_mismatch.compatible && (
        <Alert
          type="error"
          icon={<WarningOutlined />}
          message="Embedding 模型不匹配！"
          description={
            <span>
              当前使用 <Tag>{data.embedding_mismatch.current}</Tag>，
              但已有向量是用 <Tag color="red">{data.embedding_mismatch.stored}</Tag> 生成的。
              检索结果可能不准确！请前往
              <a href="/admin/documents">知识库管理</a> 重新处理所有文档。
            </span>
          }
          style={{ marginBottom: 24 }}
          showIcon
        />
      )}

      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        {/* LLM 模型选择 */}
        <Card title={<Space><SwapOutlined /> LLM 对话模型</Space>}>
          <Paragraph type="secondary">
            切换 LLM 模型即时生效，无需重启。不同模型速度和效果不同，可随时切换测试。
          </Paragraph>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <Text strong>当前模型：</Text>
            <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
              {data?.llm.current}
            </Tag>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            <Text type="secondary">切换即时生效，不影响已处理文档</Text>
          </div>

          <Select
            style={{ width: '100%' }}
            value={data?.llm.current}
            onChange={handleSwitchLLM}
            loading={switchingLLM}
            options={data?.llm.options.map((m) => ({
              value: m.value,
              label: (
                <Space direction="vertical" size={0}>
                  <Text strong>{m.label}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{m.value} — {m.desc}</Text>
                </Space>
              ),
            }))}
          />
        </Card>

        {/* Embedding 模型选择 */}
        <Card title={<Space><SwapOutlined /> Embedding 向量化模型</Space>}
          extra={
            <Tag color="orange" icon={<WarningOutlined />}>
              切换后需重新处理文档
            </Tag>
          }
        >
          <Paragraph type="secondary">
            ⚠️ Embedding 模型影响向量语义空间。切换后已有文档的向量不再匹配，
            需要在知识库管理页面重新处理所有文档，否则问答结果会不准确。
          </Paragraph>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <Text strong>当前模型：</Text>
            <Tag color="purple" style={{ fontSize: 14, padding: '4px 12px' }}>
              {data?.embedding.current}
            </Tag>
            {data?.embedding_mismatch?.compatible === false ? (
              <>
                <WarningOutlined style={{ color: '#ff4d4f' }} />
                <Text type="danger">与已存储向量不匹配</Text>
              </>
            ) : (
              <>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <Text type="success">与已存储向量一致</Text>
              </>
            )}
          </div>

          <Select
            style={{ width: '100%' }}
            value={data?.embedding.current}
            onChange={handleSwitchEmb}
            loading={switchingEmb}
            options={data?.embedding.options.map((m) => ({
              value: m.value,
              label: (
                <Space direction="vertical" size={0}>
                  <Text strong>{m.label}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{m.value} — {m.desc}</Text>
                </Space>
              ),
            }))}
          />
        </Card>

        {/* 免费额度说明 */}
        <Card title="关于免费额度" size="small">
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            以上模型在阿里云百炼平台各有 <Text strong>100万 tokens</Text> 免费额度（有效期90天）。
            LLM 模型可随时切换不影响数据；Embedding 模型切换后需要重新处理文档。
            建议先选定一个 Embedding 模型入库文档，后续用不同 LLM 模型测试问答效果。
          </Paragraph>
        </Card>
      </Space>
    </div>
  )
}
