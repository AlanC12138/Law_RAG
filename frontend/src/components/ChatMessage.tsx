import { useState } from 'react'
import type { ChatMessage as ChatMessageType } from '../types'

interface ChatMessageProps {
  message: ChatMessageType
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false)

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
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-semibold text-blue-700 truncate max-w-[60%]">
                          {src.filename}
                        </span>
                        <span className="text-blue-400 shrink-0 ml-2">
                          p.{src.page}
                          {src.section_title && ` · ${src.section_title}`}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed line-clamp-4 italic">
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
