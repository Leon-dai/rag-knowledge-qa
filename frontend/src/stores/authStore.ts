import { create } from 'zustand'
import { authAPI } from '../api/auth'

interface User {
  id: string
  username: string
  email: string | null
  role: string
  is_active: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, email?: string) => Promise<void>
  logout: () => void
  fetchMe: () => Promise<void>
  setTokens: (accessToken: string, refreshToken: string) => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
  isAuthenticated: !!localStorage.getItem('accessToken'),

  login: async (username: string, password: string) => {
    const res = await authAPI.login({ username, password })
    localStorage.setItem('accessToken', res.data.access_token)
    localStorage.setItem('refreshToken', res.data.refresh_token)
    set({
      accessToken: res.data.access_token,
      refreshToken: res.data.refresh_token,
      user: res.data.user,
      isAuthenticated: true,
    })
  },

  register: async (username: string, password: string, email?: string) => {
    await authAPI.register({ username, password, email })
  },

  logout: () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    })
  },

  fetchMe: async () => {
    try {
      const res = await authAPI.getMe()
      set({ user: res.data, isAuthenticated: true })
    } catch {
      get().logout()
    }
  },

  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem('accessToken', accessToken)
    localStorage.setItem('refreshToken', refreshToken)
    set({ accessToken, refreshToken, isAuthenticated: true })
  },
}))
