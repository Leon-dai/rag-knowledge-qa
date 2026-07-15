import { create } from 'zustand'
import { docsAPI } from '../api/docs'

interface Document {
  id: string
  original_filename: string
  file_type: string
  file_size: number
  status: string
  chunk_count: number
  created_at: string
}

interface KBState {
  documents: Document[]
  total: number
  page: number
  loading: boolean

  fetchDocuments: (page?: number, status?: string) => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  deleteDocument: (id: string) => Promise<void>
  reprocessDocument: (id: string) => Promise<void>
}

export const useKBStore = create<KBState>((set, get) => ({
  documents: [],
  total: 0,
  page: 1,
  loading: false,

  fetchDocuments: async (page = 1, status?: string) => {
    set({ loading: true })
    try {
      const res = await docsAPI.list({ page, status })
      set({
        documents: res.data.items || [],
        total: res.data.total || 0,
        page,
      })
    } catch {
      // handled in component
    } finally {
      set({ loading: false })
    }
  },

  uploadDocument: async (file: File) => {
    await docsAPI.upload(file)
    await get().fetchDocuments()
  },

  deleteDocument: async (id: string) => {
    await docsAPI.delete(id)
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== id),
      total: state.total - 1,
    }))
  },

  reprocessDocument: async (id: string) => {
    await docsAPI.reprocess(id)
    await get().fetchDocuments()
  },
}))
