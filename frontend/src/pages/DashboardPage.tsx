import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

interface Matter {
  id: string
  name: string
  client_name: string
  description: string
}

export default function DashboardPage() {
  const [matters, setMatters] = useState<Matter[]>([])
  const [selectedMatter, setSelectedMatter] = useState<Matter | null>(null)
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadMatters()
  }, [])

  const loadMatters = async () => {
    try {
      setLoading(true)
      const response = await client.get('/matters')
      setMatters(response.data || [])
    } catch (err) {
      setError('Failed to load matters')
      if ((err as any)?.response?.status === 401) {
        navigate('/login')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMatter || !question.trim()) return

    // Query endpoint integration pending
    console.log(`Query: ${question} for matter: ${selectedMatter.id}`)
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Law RAG</h1>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar - Matters List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Matters</h2>

              {loading ? (
                <div className="text-gray-600">Loading...</div>
              ) : error ? (
                <div className="text-red-600">{error}</div>
              ) : matters.length === 0 ? (
                <div className="text-gray-600">No matters available</div>
              ) : (
                <div className="space-y-2">
                  {matters.map((matter) => (
                    <button
                      key={matter.id}
                      onClick={() => setSelectedMatter(matter)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition ${
                        selectedMatter?.id === matter.id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                      }`}
                    >
                      <div className="font-semibold">{matter.name}</div>
                      <div className="text-xs opacity-75">{matter.client_name}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Main Content - Query Interface */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow p-6">
              {!selectedMatter ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-gray-600 text-lg mb-4">Select a matter to start querying</p>
                    <p className="text-gray-400">Choose a matter from the sidebar</p>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">{selectedMatter.name}</h2>
                    <p className="text-gray-600 mt-2">{selectedMatter.description || selectedMatter.client_name}</p>
                  </div>

                  <form onSubmit={handleQuerySubmit} className="space-y-4">
                    <div>
                      <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
                        Ask a Question
                      </label>
                      <textarea
                        id="question"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="What is the status of the contract terms? ..."
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                        rows={4}
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition"
                    >
                      Submit Query
                    </button>
                  </form>

                  {/* Results Area */}
                  <div className="mt-8 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-gray-600">Response will appear here after query submission</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
