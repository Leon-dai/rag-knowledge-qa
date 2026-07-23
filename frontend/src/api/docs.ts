import client from './client'

export const docsAPI = {
  list: (params?: { page?: number; size?: number; status?: string }) =>
    client.get('/docs', { params }),

  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post('/docs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },

  get: (id: string) => client.get(`/docs/${id}`),

  delete: (id: string) => client.delete(`/docs/${id}`),

  reprocess: (id: string) => client.post(`/docs/${id}/reprocess`),

  dashboard: () => client.get('/docs/dashboard'),

  dailyReview: () => client.get('/docs/daily-review'),

  reclassify: () => client.post('/docs/reclassify'),

  updateMetadata: (id: string, data: { original_filename?: string; category?: string; tags?: string[]; summary?: string }) =>
    client.patch(`/docs/${id}/metadata`, data),

  preview: (id: string) => client.get(`/docs/${id}/preview`),

  download: async (id: string, filename: string) => {
    const token = localStorage.getItem('accessToken')
    const res = await fetch(`/api/docs/${id}/file`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}
