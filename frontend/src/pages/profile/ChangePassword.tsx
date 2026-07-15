import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { authAPI } from '../../api/auth'

const { Title } = Typography

export default function ChangePassword() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: {
    old_password: string
    new_password: string
  }) => {
    setLoading(true)
    try {
      await authAPI.changePassword(values)
      message.success('密码修改成功')
      form.resetFields()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : '修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', padding: '0 24px' }}>
      <Card>
        <Title level={4} style={{ marginBottom: 24 }}>修改密码</Title>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="old_password"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            确认修改
          </Button>
        </Form>
      </Card>
    </div>
  )
}
