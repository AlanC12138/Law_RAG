import { useEffect, useRef, useState } from 'react'
import { streamQuery } from '../api/query'
import type { ConversationTurn } from '../api/query'
import ChatMessage from './ChatMessage'
import type { ChatMessage as ChatMessageType, Matter, SourceReference } from '../types'

interface ChatPanelProps {
  matter: Matter
  onSourceClick?: (src: SourceReference) => void
}

export default function ChatPanel({ matter, onSourceClick }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [question, setQuestion] = useState('')
  const [isQuerying, setIsQuerying] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reset conversation when matter changes
  useEffect(() => {
    setMessages([])
    setQuestion('')
  }, [matter.id])

  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    const q = question.trim()
    if (!q || isQuerying) return

    const msgId = crypto.randomUUID()
    setQuestion('')
    setIsQuerying(true)

    // Build history from all completed turns so the LLM has conversation context
    const history: ConversationTurn[] = messages
      .filter((m) => !m.isStreaming && m.answer)
      .flatMap((m) => [
        { role: 'user' as const,      content: m.question },
        { role: 'assistant' as const, content: m.answer   },
      ])

    // Add placeholder message immediately
    setMessages((prev) => [
      ...prev,
      {
        id: msgId,
        question: q,
        answer: '',
        sources: [],
        isStreaming: true,
        timestamp: new Date(),
      },
    ])

    await streamQuery(matter.id, q, history, {
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId ? { ...m, answer: m.answer + token } : m
          )
        )
      },
      onSources: (sources: SourceReference[]) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === msgId ? { ...m, sources } : m))
        )
      },
      onDone: () => {
        setMessages((prev) =>
          prev.map((m) => (m.id === msgId ? { ...m, isStreaming: false } : m))
        )
        setIsQuerying(false)
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId
              ? {
                  ...m,
                  answer: `Error: ${err.message}`,
                  isStreaming: false,
                }
              : m
          )
        )
        setIsQuerying(false)
      },
    })
  }

  // Submit on Enter (Shift+Enter for newline)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="w-14 h-14 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
              <svg className="w-7 h-7 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h3 className="text-base font-semibold text-slate-700 mb-1">
              Ask about {matter.name}
            </h3>
            <p className="text-sm text-slate-400 max-w-xs">
              Ask any question about the documents in this matter. Answers include source citations.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {[
                'What are the key indemnification terms?',
                'Summarise the termination clauses',
                'What governing law applies?',
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => setQuestion(hint)}
                  className="text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded-full px-3 py-1.5 hover:bg-blue-100 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} onSourceClick={onSourceClick} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-blue-100 bg-white px-4 py-3">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about this matter… (Enter to send)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white transition max-h-32 overflow-y-auto"
            style={{ lineHeight: '1.5' }}
            disabled={isQuerying}
          />
          <button
            type="submit"
            disabled={!question.trim() || isQuerying}
            className="shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors shadow-sm"
          >
            {isQuerying ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </button>
        </form>
        <p className="text-xs text-slate-300 mt-1.5 ml-1">Shift+Enter for newline</p>
      </div>
    </div>
  )
}
