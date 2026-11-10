import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [threadId, setThreadId] = useState('')
  const [answer, setAnswer] = useState('')

  // 首次发起规划
  const handlePlan = async () => {
    if (!input.trim()) return
    setLoading(true)
    setResult('')
    setQuestion('')
    setStatus('正在连接…')

    try {
      const res = await fetch('/api/plan/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: input }),
      })
      await processStream(res)
    } catch (e) {
      setStatus('请求失败：' + e.message)
    } finally {
      setLoading(false)
    }
  }

  // 回答追问后恢复
  const handleResume = async () => {
    if (!answer.trim() || !threadId) return
    setLoading(true)
    setStatus('正在继续规划…')

    try {
      const res = await fetch(`/api/plan/${threadId}/resume/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer }),
      })
      await processStream(res)
    } catch (e) {
      setStatus('请求失败：' + e.message)
    } finally {
      setLoading(false)
    }
  }

  // 处理 SSE 流
  const processStream = async (res) => {
    if (!res.body) throw new Error('浏览器不支持流式读取')
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        const jsonStr = line.slice(5).trim()
        try {
          handleMessage(JSON.parse(jsonStr))
        } catch (e) {
          // 忽略解析失败
        }
      }
    }
  }

  const handleMessage = (msg) => {
    switch (msg.type) {
      case 'start':
        setThreadId(msg.thread_id)
        break
      case 'status':
        setStatus(msg.message)
        break
      case 'clarify':
        setQuestion(msg.question)
        setAnswer('')
        setStatus('')
        break
      case 'guide_start':
        // 攻略正文开始流式输出，清空旧内容准备接收
        setResult('')
        break
      case 'guide_token':
        // 逐 token 追加攻略正文
        setResult((prev) => prev + msg.token)
        break
      case 'done':
        // 流式完成，用最终完整攻略兜底（防止最后有 token 遗漏）
        if (msg.guide_markdown) {
          setResult(msg.guide_markdown)
        } else if (!result) {
          setResult('（未生成内容）')
        }
        setStatus('完成')
        setQuestion('')
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

      {question && (
        <div className="clarify-box">
          <p className="clarify-q">🤔 {question}</p>
          <input
            type="text"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="请输入你的回答，例如：去成都，玩3天，预算2000"
          />
          <button onClick={handleResume} disabled={loading}>
            {loading ? '继续规划中…' : '提交回答'}
          </button>
        </div>
      )}

      {result && (
        <div className="result">
          <ReactMarkdown>{result}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}

export default App
