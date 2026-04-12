import client from './client'
import type { Matter } from '../types'

export const mattersApi = {
  list: async (): Promise<Matter[]> => {
    const res = await client.get('/matters')
    return res.data
  },

  get: async (matterId: string): Promise<Matter> => {
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
}
