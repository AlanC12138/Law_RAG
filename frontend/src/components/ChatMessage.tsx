import { useState } from 'react'
import type { ChatMessage as ChatMessageType, SourceReference } from '../types'

interface ChatMessageProps {
  message: ChatMessageType
  onSourceClick?: (src: SourceReference) => void
}

export default function ChatMessage({ message, onSourceClick }: ChatMessageProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 1500)
  }

  return (
    <div className="space-y-3">
      {/* Question bubble */}
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed">{message.question}</p>
        </div>
      </div>

      {/* Answer bubble */}
      <div className="flex justify-start">
        <div className="max-w-[85%] space-y-2">
          <div className="bg-white border border-blue-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
            {message.isStreaming && message.answer === '' ? (
              <div className="flex items-center gap-1.5 py-1">
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            ) : (
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                {message.answer}
                {message.isStreaming && (
                  <span className="inline-block w-0.5 h-4 bg-blue-500 ml-0.5 animate-pulse align-text-bottom" />
                )}
              </p>
            )}
          </div>

          {/* Sources toggle */}
          {!message.isStreaming && message.sources.length > 0 && (
            <div>
              <button
                onClick={() => setSourcesOpen((o) => !o)}
                className="flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-700 font-medium px-1 transition-colors"
              >
                <svg
                  className={`w-3.5 h-3.5 transition-transform ${sourcesOpen ? 'rotate-90' : ''}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
              </button>

              {sourcesOpen && (
                <div className="mt-2 space-y-2">
                  {message.sources.map((src, i) => (
                    <div
                      key={i}
                      className="bg-blue-50 border border-blue-100 rounded-xl p-3 text-xs"
                    >
                      {/* Header: filename · page + action buttons */}
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-semibold text-blue-700 truncate max-w-[55%]">
                          {src.filename}
                        </span>
                        <div className="flex items-center gap-1 shrink-0 ml-2">
                          <span className="text-blue-400">
                            p.{src.page}
                            {src.section_title && ` · ${src.section_title}`}
                          </span>

                          {/* Copy passage */}
                          <button
                            onClick={() => handleCopy(src.passage, i)}
                            title="Copy passage"
                            className="p-1 rounded text-blue-400 hover:text-blue-700 hover:bg-blue-100 transition-colors"
                          >
                            {copiedIdx === i ? (
                              <svg className="w-3.5 h-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                                />
                              </svg>
                            )}
                          </button>

                          {/* Jump to document */}
                          {onSourceClick && (
                            <button
                              onClick={() => onSourceClick(src)}
                              title="View in Documents tab"
                              className="p-1 rounded text-blue-400 hover:text-blue-700 hover:bg-blue-100 transition-colors"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Full passage — no line-clamp */}
                      <p className="text-slate-600 leading-relaxed italic">
                        "{src.passage}"
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <p className="text-xs text-slate-300 px-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    </div>
  )
}
