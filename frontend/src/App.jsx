import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  const handlePlan = async () => {
    if (!input.trim()) return
    setLoading(true)
    setResult('')
    try {
      const res = await fetch('/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: input }),
      })
      const data = await res.json()
      if (data.guide_markdown) {
        setResult(data.guide_markdown)
      } else {
        setResult('规划完成，但未生成攻略内容。')
      }
    } catch (e) {
      setResult('请求失败：' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>🧳 旅行规划 Agent</h1>
      <p className="subtitle">多智能体旅行规划（LangGraph + FastAPI + MCP）</p>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="例如：武汉出发，3天，预算3000，想看江景和历史景点"
        rows={4}
      />
      <button onClick={handlePlan} disabled={loading}>
        {loading ? '规划中…（约需几十秒）' : '开始规划'}
      </button>
      {result && (
        <div className="result">
          <ReactMarkdown>{result}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}

export default App
