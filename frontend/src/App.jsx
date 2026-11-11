import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [threadId, setThreadId] = useState('')
  const [answer, setAnswer] = useState('')
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  // 加载历史会话列表
  const loadHistory = async () => {
    try {
      const res = await fetch('/api/history')
      const data = await res.json()
      setHistory(data.items || [])
      setShowHistory(true)
    } catch (e) {
      setStatus('加载历史失败：' + e.message)
    }
  }

  // 查看某次历史会话的完整攻略
  const viewHistory = async (tid) => {
    setStatus('正在加载历史攻略…')
    try {
      const res = await fetch(`/api/plan/${tid}`)
      if (!res.ok) throw new Error('未找到该会话')
      const data = await res.json()
      setResult(data.guide_markdown || '（该会话无攻略内容）')
      setThreadId(tid)
      setStatus('已加载历史攻略')
    } catch (e) {
      setStatus('加载失败：' + e.message)
    }
  }

  // 复用历史需求：把历史输入回填到输入框
  const reuseHistory = (userInput) => {
    setInput(userInput)
    setShowHistory(false)
    setResult('')
    setStatus('已回填历史需求，可修改后重新规划')
  }

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
      <button onClick={loadHistory} disabled={loading} className="secondary-btn">
        历史记录
      </button>

      {status && <div className="status">{status}</div>}

      {showHistory && (
        <div className="history-panel">
          <div className="history-header">
            <h2>📋 历史规划</h2>
            <button onClick={() => setShowHistory(false)} className="close-btn">
              收起
            </button>
          </div>
          {history.length === 0 ? (
            <p className="history-empty">暂无历史记录，先去规划一次吧～</p>
          ) : (
            <ul className="history-list">
              {history.map((item) => (
                <li key={item.thread_id} className="history-item">
                  <div className="history-info">
                    <div className="history-input">{item.user_input}</div>
                    <div className="history-meta">
                      {item.destination && <span>📍 {item.destination}</span>}
                      {item.days && <span>📅 {item.days} 天</span>}
                      {item.budget != null && <span>💰 ¥{item.budget}</span>}
                      <span className="history-time">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="history-actions">
                    {item.has_result && (
                      <button onClick={() => viewHistory(item.thread_id)} className="mini-btn">
                        查看攻略
                      </button>
                    )}
                    <button onClick={() => reuseHistory(item.user_input)} className="mini-btn">
                      复用
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

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
