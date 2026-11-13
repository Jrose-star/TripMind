import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const EXAMPLE_TEMPLATES = [
  { label: '武汉 3 日', text: '武汉出发，3天，预算3000，想看江景和历史景点' },
  { label: '成都 2 日', text: '去成都玩2天，预算2000，想吃美食和看熊猫' },
  { label: '北京 4 日', text: '北京4天，预算5000，带父母，想去故宫长城' },
]

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
  const [steps, setSteps] = useState([]) // 执行步骤进度
  const resultRef = useRef(null)

  // 攻略输出时自动滚动到底部
  useEffect(() => {
    if (resultRef.current) {
      resultRef.current.scrollTop = resultRef.current.scrollHeight
    }
  }, [result])

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
      setShowHistory(false)
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
    setSteps([])
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
        // 根据状态文字推断当前步骤
        updateStep(msg.message)
        break
      case 'clarify':
        setQuestion(msg.question)
        setAnswer('')
        setStatus('')
        break
      case 'guide_start':
        setResult('')
        break
      case 'guide_token':
        setResult((prev) => prev + msg.token)
        break
      case 'done':
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

  // 将后端状态信息映射为可读的步骤进度
  const updateStep = (message) => {
    const mapping = [
      { key: '解析需求', pattern: /解析|需求|理解/ },
      { key: '检索地点', pattern: /检索|POI|地点|搜索/ },
      { key: '查询天气', pattern: /天气/ },
      { key: '生成攻略', pattern: /攻略|生成|规划|撰写/ },
    ]
    for (const m of mapping) {
      if (m.pattern.test(message)) {
        setSteps((prev) => {
          if (prev.some((s) => s.key === m.key)) return prev
          return [...prev, { key: m.key, done: false }]
        })
      }
    }
  }

  // 快捷模板点击
  const pickTemplate = (text) => {
    setInput(text)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">🧳</span>
          <div>
            <div className="brand-title">旅行规划 Agent</div>
            <div className="brand-sub">LangGraph · FastAPI · MCP</div>
          </div>
        </div>
        <button className="ghost-btn" onClick={loadHistory} disabled={loading}>
          🕘 历史记录
        </button>
      </header>

      <main className="main">
        {/* 输入卡片 */}
        <section className="input-card">
          <h2 className="card-title">想去哪儿？</h2>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="例如：武汉出发，3天，预算3000，想看江景和历史景点"
            rows={3}
          />
          <div className="templates">
            {EXAMPLE_TEMPLATES.map((t) => (
              <button
                key={t.label}
                className="chip"
                onClick={() => pickTemplate(t.text)}
                disabled={loading}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="input-actions">
            <button className="primary-btn" onClick={handlePlan} disabled={loading}>
              {loading ? '规划中…' : '✨ 开始规划'}
            </button>
            {input && (
              <button className="ghost-btn" onClick={() => setInput('')} disabled={loading}>
                清空
              </button>
            )}
          </div>
        </section>

        {/* 状态提示 */}
        {status && (
          <div className={`status ${status === '完成' ? 'status-ok' : ''}`}>
            {loading && <span className="spinner" />}
            {status}
          </div>
        )}

        {/* 步骤进度 */}
        {steps.length > 0 && loading && (
          <div className="steps">
            {steps.map((s, i) => (
              <span key={s.key} className="step-chip">
                <span className="step-dot" />
                {s.key}
              </span>
            ))}
          </div>
        )}

        {/* 追问框 */}
        {question && (
          <div className="clarify-box">
            <p className="clarify-q">🤔 {question}</p>
            <input
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="请输入你的回答，例如：去成都，玩3天，预算2000"
              onKeyDown={(e) => e.key === 'Enter' && handleResume()}
            />
            <button className="primary-btn" onClick={handleResume} disabled={loading}>
              {loading ? '继续规划中…' : '提交回答'}
            </button>
          </div>
        )}

        {/* 攻略结果 */}
        {result && (
          <section className="result-card">
            <div className="result-header">
              <span className="result-title">📄 旅行攻略</span>
              <button
                className="ghost-btn"
                onClick={() => {
                  const blob = new Blob([result], { type: 'text/markdown' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = '旅行攻略.md'
                  a.click()
                  URL.revokeObjectURL(url)
                }}
              >
                ⬇ 导出
              </button>
            </div>
            <div className="result-body" ref={resultRef}>
              <ReactMarkdown>{result}</ReactMarkdown>
            </div>
          </section>
        )}
      </main>

      {/* 历史记录侧边栏 */}
      {showHistory && (
        <div className="drawer-overlay" onClick={() => setShowHistory(false)}>
          <aside className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h2>🕘 历史规划</h2>
              <button className="ghost-btn" onClick={() => setShowHistory(false)}>
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
                        <button
                          onClick={() => viewHistory(item.thread_id)}
                          className="mini-btn"
                        >
                          查看
                        </button>
                      )}
                      <button
                        onClick={() => reuseHistory(item.user_input)}
                        className="mini-btn ghost"
                      >
                        复用
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

export default App
