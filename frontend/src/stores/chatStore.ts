import { create } from 'zustand'
import { chatAPI } from '../api/chat'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: any[] | null
  created_at: string
}

interface Session {
  id: string
  title: string
  message_count: number
  updated_at: string
  created_at: string
}

interface ChatState {
  sessions: Session[]
  currentSession: Session | null
  messages: Message[]
  streamingContent: string
  isStreaming: boolean
  statusText: string
  loading: boolean
  // 搜索高亮：{ q: 搜索词, msg: 匹配的消息 ID }
  searchHighlight: { q: string; msg: string } | null

  fetchSessions: () => Promise<void>
  createSession: () => Promise<void>
  selectSession: (sessionId: string) => void
  fetchMessages: (sessionId: string) => Promise<void>
  sendMessage: (sessionId: string, content: string, searchMode?: 'local' | 'web' | 'mixed') => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  renameSession: (sessionId: string, title: string) => Promise<void>
  setSearchHighlight: (data: { q: string; msg: string } | null) => void
}

let abortController: AbortController | null = null

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  streamingContent: '',
  isStreaming: false,
  statusText: '',
  loading: false,
  searchHighlight: null,

  setSearchHighlight: (data) => set({ searchHighlight: data }),

  fetchSessions: async () => {
    try {
      const res = await chatAPI.listSessions()
      set({ sessions: res.data.items || [] })
    } catch {
      // 静默失败
    }
  },

  createSession: async () => {
    const res = await chatAPI.createSession()
    const session = res.data
    set((state) => ({
      // 清理旧空对话，只保留有内容的
      sessions: [session, ...state.sessions.filter(s => s.message_count > 0)],
      currentSession: session,
      messages: [],
      loading: false,
    }))
  },

  selectSession: (sessionId: string) => {
    const session = get().sessions.find((s) => s.id === sessionId)
    if (session) set({ currentSession: session })
  },

  fetchMessages: async (sessionId: string) => {
    set({ loading: true })
    try {
      const res = await chatAPI.getMessages(sessionId)
      set({ messages: res.data.items || [] })
    } catch {
      set({ messages: [] })
    } finally {
      set({ loading: false })
    }
  },

  sendMessage: async (sessionId: string, content: string, searchMode: 'local' | 'web' | 'mixed' = 'local') => {
    // 中断上一个流
    if (abortController) {
      abortController.abort()
    }

    // 如果正在流式输出，把当前已输出的内容保存为一条消息
    const currentStreaming = get().streamingContent
    if (currentStreaming) {
      const partialMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: currentStreaming + ' [已中断]',
        citations: null,
        created_at: new Date().toISOString(),
      }
      set((state) => ({
        messages: [...state.messages, partialMsg],
        streamingContent: '',
        isStreaming: false,
      }))
    }

    // 添加用户消息
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      citations: null,
      created_at: new Date().toISOString(),
    }
    set((state) => ({
      messages: [...state.messages, userMsg],
      streamingContent: '',
      isStreaming: true,
    }))

    abortController = new AbortController()

    try {
      const token = localStorage.getItem('accessToken')
      const response = await fetch(`/api/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ content, search_mode: searchMode }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || '请求失败')
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('不支持流式响应')
      }

      const decoder = new TextDecoder()
      let fullContent = ''
      let citations: any[] = []
      let lineBuffer = ''
      let saved = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        lineBuffer += decoder.decode(value, { stream: true })
        const lines = lineBuffer.split('\n')
        lineBuffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6))
              if (data.token) {
                fullContent += data.token
                set({ streamingContent: fullContent })
              } else if (data.status) {
                set({ statusText: data.status })
              } else if (data.sources) {
                citations = data.sources
              } else if (data.done) {
                saved = true
                const assistantMsg: Message = {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: fullContent,
                  citations,
                  created_at: new Date().toISOString(),
                }
                set((state) => ({
                  messages: [...state.messages, assistantMsg],
                  streamingContent: '',
                  isStreaming: false,
                  statusText: '',
                }))
              }
            } catch {
              // 忽略解析错误
            }
          }
        }
      }

      // 如果没收到 done 事件，补保存消息
      if (!saved && fullContent) {
        const assistantMsg: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: fullContent,
          citations,
          created_at: new Date().toISOString(),
        }
        set((state) => ({
          messages: [...state.messages, assistantMsg],
          streamingContent: '',
          isStreaming: false,
          statusText: '',
        }))
      }

      // 刷新会话列表以更新标题
      get().fetchSessions()
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // 用户主动中断，静默处理
        return
      }
      set({ streamingContent: '', isStreaming: false })
      throw err
    }
  },

  deleteSession: async (sessionId: string) => {
    await chatAPI.deleteSession(sessionId)
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== sessionId),
      currentSession: state.currentSession?.id === sessionId ? null : state.currentSession,
      messages: state.currentSession?.id === sessionId ? [] : state.messages,
    }))
  },

  renameSession: async (sessionId: string, title: string) => {
    await chatAPI.updateSession(sessionId, { title })
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, title } : s
      ),
      currentSession: state.currentSession?.id === sessionId
        ? { ...state.currentSession, title }
        : state.currentSession,
    }))
  },
}))
