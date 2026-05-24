import client from './client'
import type { Document } from '../types'

export const documentsApi = {
  list: async (matterId: string): Promise<Document[]> => {
    const res = await client.get(`/matters/${matterId}/documents`)
    return res.data
  },

  upload: async (matterId: string, file: File): Promise<Document> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post(`/matters/${matterId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  remove: async (matterId: string, docId: string): Promise<void> => {
    await client.delete(`/matters/${matterId}/documents/${docId}`)
  },
}
