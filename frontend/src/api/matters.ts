import client from './client'
import type { Matter, MatterDetail } from '../types'

export const mattersApi = {
  list: async (): Promise<Matter[]> => {
    const res = await client.get('/matters')
    return res.data
  },

  get: async (matterId: string): Promise<MatterDetail> => {
    const res = await client.get(`/matters/${matterId}`)
    return res.data
  },

  create: async (data: {
    name: string
    client_name: string
    description?: string
    jurisdiction?: string
  }): Promise<Matter> => {
    const res = await client.post('/matters', data)
    return res.data
  },

  addMember: async (matterId: string, userId: string): Promise<void> => {
    await client.post(`/matters/${matterId}/members`, { user_id: userId })
  },

  removeMember: async (matterId: string, userId: string): Promise<void> => {
    await client.delete(`/matters/${matterId}/members/${userId}`)
  },

  deleteMatter: async (matterId: string): Promise<void> => {
    await client.delete(`/matters/${matterId}`)
  },
}
