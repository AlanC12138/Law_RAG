import client from './client'
import type { User, UserRole } from '../types'

export const usersApi = {
  me: async (): Promise<User> => {
    const res = await client.get('/users/me')
    return res.data
  },

  list: async (): Promise<User[]> => {
    const res = await client.get('/users')
    return res.data
  },

  create: async (data: {
    email: string
    password: string
    full_name: string
    role: UserRole
  }): Promise<User> => {
    const res = await client.post('/users', data)
    return res.data
  },

  updateRole: async (userId: string, role: UserRole): Promise<User> => {
    const res = await client.patch(`/users/${userId}`, { role })
    return res.data
  },

  deactivate: async (userId: string): Promise<User> => {
    const res = await client.delete(`/users/${userId}/deactivate`)
    return res.data
  },
}
