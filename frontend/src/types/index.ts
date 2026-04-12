// ---------------------------------------------------------------------------
// Domain types shared across the frontend
// ---------------------------------------------------------------------------

export interface Matter {
  id: string
  name: string
  client_name: string
  description: string
  jurisdiction: string
  is_active: boolean
  created_at: string
}

export interface Document {
  id: string
  filename: string
  file_type: string
  status: 'pending' | 'processing' | 'ready' | 'failed'
  page_count: number
  created_at: string
}

export interface SourceReference {
  doc_id: string
  filename: string
  page: number
  section_title: string
  passage: string
}

export interface ChatMessage {
  id: string
  question: string
  answer: string
  sources: SourceReference[]
  isStreaming: boolean
  timestamp: Date
}

export interface User {
  id: string
  email: string
  full_name: string
  role: 'partner' | 'associate' | 'paralegal'
}
