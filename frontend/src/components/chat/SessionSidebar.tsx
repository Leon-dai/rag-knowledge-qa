import { Button, List, Typography, Popconfirm, Space } from 'antd'
import { PlusOutlined, DeleteOutlined, MessageOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import dayjs from 'dayjs'

const { Text } = Typography

export default function SessionSidebar() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()
  const { sessions, createSession, deleteSession } = useChatStore()

  const handleCreate = async () => {
    await createSession()
    const { currentSession } = useChatStore.getState()
    if (currentSession) {
      navigate(`/chat/${currentSession.id}`)
    }
  }

  const handleDelete = async (id: string) => {
    await deleteSession(id)
    if (sessionId === id) {
      navigate('/chat')
    }
  }

  return (
    <div style={{
      width: 280,
      minWidth: 280,
      borderRight: '1px solid #f0f0f0',
      background: '#fafafa',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ padding: '16px' }}>
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleCreate}
          block
        >
          新建对话
        </Button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <List
          dataSource={sessions}
          renderItem={(session) => (
            <List.Item
              onClick={() => navigate(`/chat/${session.id}`)}
              style={{
                cursor: 'pointer',
                padding: '12px 16px',
                background: sessionId === session.id ? '#e6f4ff' : 'transparent',
                borderLeft: sessionId === session.id ? '3px solid #1677ff' : '3px solid transparent',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ width: '100%', overflow: 'hidden' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text
                    strong
                    ellipsis={{ tooltip: session.title }}
                    style={{ maxWidth: 180, fontSize: 13 }}
                  >
                    <MessageOutlined style={{ marginRight: 6 }} />
                    {session.title}
                  </Text>
                  <Popconfirm
                    title="确定删除此对话？"
                    onConfirm={(e) => {
                      e?.stopPropagation()
                      handleDelete(session.id)
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>
                </Space>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {dayjs(session.updated_at).format('MM-DD HH:mm')}
                  {' · '}
                  {session.message_count} 条消息
                </Text>
              </div>
            </List.Item>
          )}
          locale={{ emptyText: '暂无对话' }}
        />
      </div>
    </div>
  )
}
