import client from './client'

export const authAPI = {
  register: (data: { username: string; password: string; email?: string }) =>
    client.post('/auth/register', data),

  login: (data: { username: string; password: string }) =>
    client.post('/auth/login', data),

  refresh: (refreshToken: string) =>
    client.post('/auth/refresh', { refresh_token: refreshToken }),

  changePassword: (data: { old_password: string; new_password: string }) =>
    client.post('/auth/change-password', data),

  getMe: () => client.get('/auth/me'),
}
