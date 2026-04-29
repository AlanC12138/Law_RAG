import client from './client'
import type { QueryLog, SourceReference } from '../types'

// Uses raw fetch (not Axios) so we can read the SSE stream incrementally.

export interface ConversationTurn {
  role: 'user' | 'assistant'
  content: string
}

interface StreamCallbacks {
  onToken: (token: string) => void
  onSources: (sources: SourceReference[]) => void
  onDone: () => void
  onError: (err: Error) => void
}

export async function streamQuery(
  matterId: string,
  question: string,
  history: ConversationTurn[],
  callbacks: StreamCallbacks
): Promise<void> {
  const token = localStorage.getItem('access_token')

  const response = await fetch(`/api/v1/matters/${matterId}/query?stream=true`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, history }),
  })

  if (!response.ok) {
    const text = await response.text()
    callbacks.onError(new Error(`Query failed (${response.status}): ${text}`))
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError(new Error('No response body'))
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE lines end with \n\n — process all complete events in the buffer
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''   // keep the last incomplete chunk

      for (const part of parts) {
        for (const line of part.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'token') callbacks.onToken(data.content)
            else if (data.type === 'sources') callbacks.onSources(data.content)
            else if (data.type === 'done') callbacks.onDone()
          } catch {
            // malformed JSON — skip
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export const queryApi = {
  fetchLogs: async (matterId: string): Promise<QueryLog[]> => {
    const res = await client.get(`/matters/${matterId}/query/logs`)
    return res.data
  },
}
