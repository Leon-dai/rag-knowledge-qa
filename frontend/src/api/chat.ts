import client from './client'

export const chatAPI = {
  listSessions: (params?: { page?: number; size?: number }) =>
    client.get('/sessions', { params }),

  createSession: () => client.post('/sessions'),

  getSession: (id: string) => client.get(`/sessions/${id}`),

  updateSession: (id: string, data: { title?: string }) =>
    client.put(`/sessions/${id}`, data),

  deleteSession: (id: string) => client.delete(`/sessions/${id}`),

  getMessages: (sessionId: string, params?: { page?: number; size?: number }) =>
    client.get(`/sessions/${sessionId}/messages`, { params }),

  sendMessage: (sessionId: string, content: string) =>
    client.post(`/sessions/${sessionId}/messages`, { content }, {
      responseType: 'stream',
      headers: { Accept: 'text/event-stream' },
    }),

  searchSessions: (q: string) =>
    client.get('/search', { params: { q } }),
}
