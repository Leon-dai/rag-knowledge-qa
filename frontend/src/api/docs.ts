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
}
