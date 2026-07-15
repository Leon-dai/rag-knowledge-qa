import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Typography, Spin } from 'antd'
import {
  UserOutlined, FileTextOutlined, MessageOutlined,
  DatabaseOutlined, FileDoneOutlined
} from '@ant-design/icons'
import { adminAPI } from '../../api/admin'

const { Title } = Typography

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminAPI.getStats().then((res) => {
      setStats(res.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>系统仪表盘</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="用户总数"
              value={stats?.user_count || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="文档总数"
              value={stats?.document_count || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="向量分块总数"
              value={stats?.chunk_count || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="会话总数"
              value={stats?.session_count || 0}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="消息总数"
              value={stats?.message_count || 0}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="就绪文档"
              value={stats?.ready_document_count || 0}
              prefix={<FileDoneOutlined />}
              suffix="篇"
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
