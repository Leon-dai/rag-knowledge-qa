import client from './client'

export const adminAPI = {
  getStats: () => client.get('/admin/stats'),

  listUsers: (params?: { page?: number; size?: number }) =>
    client.get('/admin/users', { params }),

  updateUserStatus: (userId: string, isActive: boolean) =>
    client.put(`/admin/users/${userId}/status`, { is_active: isActive }),

  // 模型管理
  getModels: () => client.get('/admin/models'),
  switchLLM: (model: string) => client.put('/admin/models/llm', { model }),
  switchEmbedding: (model: string) => client.put('/admin/models/embedding', { model }),
}
