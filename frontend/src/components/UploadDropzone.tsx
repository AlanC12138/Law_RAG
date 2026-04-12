import { useRef, useState } from 'react'

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void
  uploading: boolean
}

export default function UploadDropzone({ onUpload, uploading }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files).filter(isAllowed)
    if (files.length) onUpload(files)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []).filter(isAllowed)
    if (files.length) onUpload(files)
    e.target.value = ''
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      className={`
        relative border-2 border-dashed rounded-xl px-6 py-10 text-center
        transition-all duration-150 cursor-pointer select-none
        ${isDragging
          ? 'border-blue-400 bg-blue-50 scale-[1.01]'
          : 'border-blue-200 bg-white hover:border-blue-400 hover:bg-blue-50'
        }
        ${uploading ? 'pointer-events-none opacity-60' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc"
        onChange={handleChange}
        className="hidden"
      />

      <div className="flex flex-col items-center gap-3">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
          isDragging ? 'bg-blue-200' : 'bg-blue-100'
        }`}>
          {uploading ? (
            <svg className="w-6 h-6 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          ) : (
            <svg className="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700">
            {uploading ? 'Uploading…' : isDragging ? 'Drop files here' : 'Drop files or click to browse'}
          </p>
          <p className="text-xs text-slate-400 mt-1">PDF, DOCX — multiple files supported</p>
        </div>
      </div>
    </div>
  )
}

function isAllowed(file: File): boolean {
  return /\.(pdf|docx|doc)$/i.test(file.name)
}
