import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const handlePlan = async () => {
    if (!input.trim()) return
    setLoading(true)
    setResult('')
    setStatus('正在连接…')

    try {
      const res = await fetch('/api/plan/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: input }),
      })

      if (!res.body) {
        throw new Error('浏览器不支持流式读取')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 按 SSE 的 \n\n 分割消息
        const parts = buffer.split('\n\n')
        buffer = parts.pop() // 最后一段可能不完整，留到下次

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data:')) continue
          const jsonStr = line.slice(5).trim()
          try {
            const msg = JSON.parse(jsonStr)
            handleMessage(msg)
          } catch (e) {
            // 忽略解析失败的消息
          }
        }
      }
    } catch (e) {
      setStatus('请求失败：' + e.message)
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  const handleMessage = (msg) => {
    switch (msg.type) {
      case 'status':
        setStatus(msg.message)
        break
      case 'done':
        setResult(msg.guide_markdown || '（未生成内容）')
        setStatus('完成')
        break
      case 'error':
        setStatus('出错：' + msg.message)
        break
      default:
        break
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
        {loading ? '规划中…' : '开始规划'}
      </button>

      {status && <div className="status">{status}</div>}

      {result && (
        <div className="result">
          <ReactMarkdown>{result}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}

export default App
