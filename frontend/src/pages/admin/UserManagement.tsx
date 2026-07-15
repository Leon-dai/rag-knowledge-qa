import { useEffect, useState } from 'react'
import { Card, Table, Button, Tag, Space, Typography, message, Switch } from 'antd'
import { adminAPI } from '../../api/admin'

const { Title } = Typography

export default function UserManagement() {
  const [users, setUsers] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  const fetchUsers = (p: number = 1) => {
    setLoading(true)
    adminAPI.listUsers({ page: p, size: 20 })
      .then((res) => {
        setUsers(res.data.items || [])
        setTotal(res.data.total || 0)
      })
      .catch(() => message.error('获取用户列表失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchUsers(page) }, [page])

  const toggleStatus = async (userId: string, isActive: boolean) => {
    try {
      await adminAPI.updateUserStatus(userId, isActive)
      message.success(`用户已${isActive ? '启用' : '禁用'}`)
      fetchUsers(page)
    } catch {
      message.error('操作失败')
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      render: (t: string | null) => t || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (r: string) => (
        <Tag color={r === 'admin' ? 'red' : 'blue'}>
          {r === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'status',
      render: (active: boolean, record: any) => (
        <Switch
          checked={active}
          disabled={record.role === 'admin'}
          onChange={(checked) => toggleStatus(record.id, checked)}
        />
      ),
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created',
      render: (t: string) => t ? new Date(t).toLocaleDateString('zh-CN') : '-',
    },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>用户管理</Title>
      <Card>
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: (p) => setPage(p),
            showTotal: (t) => `共 ${t} 个用户`,
          }}
        />
      </Card>
    </div>
  )
}
