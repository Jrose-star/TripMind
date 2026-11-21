import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const EXAMPLE_TEMPLATES = [
  { label: '武汉 3 日', text: '武汉出发，3天，预算3000，想看江景和历史景点' },
  { label: '成都 2 日', text: '去成都玩2天，预算2000，想吃美食和看熊猫' },
  { label: '北京 4 日', text: '北京4天，预算5000，带父母，想去故宫长城' },
]

// 消息类型：user = 用户，agent = Agent 回复
// agent 消息可能包含：正文文本、追问问题、步骤进度、攻略 markdown
function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [threadId, setThreadId] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [history, setHistory] = useState([])

  const listRef = useRef(null)
  const inputRef = useRef(null)

  // 消息列表变化时自动滚动到底部
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  // 追加/更新一条消息（返回新消息 id，供流式更新使用）
  const pushMessage = (msg) => {
    let id
    setMessages((prev) => {
      id = prev.length
      return [...prev, msg]
    })
    return id
  }

  // 更新某条消息的字段（用于流式追加 token、更新状态等）
  const patchMessage = (id, patch) => {
    setMessages((prev) =>
      prev.map((m, i) => (i === id ? { ...m, ...patch } : m)),
    )
  }

  // 加载历史会话列表
  const loadHistory = async () => {
    try {
      const res = await fetch('/api/history')
      const data = await res.json()
      setHistory(data.items || [])
      setShowHistory(true)
    } catch (e) {
      pushMessage({ role: 'agent', text: '加载历史失败：' + e.message })
    }
  }

  // 查看某次历史会话的完整攻略
  const viewHistory = async (tid) => {
    try {
      const res = await fetch(`/api/plan/${tid}`)
      if (!res.ok) throw new Error('未找到该会话')
      const data = await res.json()
      setShowHistory(false)
      setMessages((prev) => [
        ...prev,
        { role: 'user', text: data.user_input || '（历史会话）' },
        { role: 'agent', text: data.guide_markdown || '（该会话无攻略内容）', kind: 'guide' },
      ])
    } catch (e) {
      pushMessage({ role: 'agent', text: '加载失败：' + e.message })
    }
  }

  // 复用历史需求：回填到输入框
  const reuseHistory = (userInput) => {
    setInput(userInput)
    setShowHistory(false)
    inputRef.current?.focus()
  }

  // 发起一次规划（首次）
  const handlePlan = async (text) => {
    const content = (text ?? input).trim()
    if (!content || loading) return
    setLoading(true)

    // 用户消息上屏
    pushMessage({ role: 'user', text: content })
    setInput('')

    // Agent 占位消息，用于流式填充
    const agentId = pushMessage({
      role: 'agent',
      text: '',
      status: '正在连接…',
      kind: 'thinking',
    })

    try {
      const res = await fetch('/api/plan/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: content, thread_id: threadId || undefined }),
      })
      await processStream(res, agentId)
    } catch (e) {
      patchMessage(agentId, { status: '', text: '请求失败：' + e.message, kind: 'error' })
    } finally {
      setLoading(false)
    }
  }

  // 回答追问后恢复
  const handleResume = async (text) => {
    const content = (text ?? input).trim()
    if (!content || loading || !threadId) return
    setLoading(true)

    pushMessage({ role: 'user', text: content })
    setInput('')

    const agentId = pushMessage({
      role: 'agent',
      text: '',
      status: '正在继续规划…',
      kind: 'thinking',
    })

    try {
      const res = await fetch(`/api/plan/${threadId}/resume/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer: content }),
      })
      await processStream(res, agentId)
    } catch (e) {
      patchMessage(agentId, { status: '', text: '请求失败：' + e.message, kind: 'error' })
    } finally {
      setLoading(false)
    }
  }

  // 处理 SSE 流
  const processStream = async (res, agentId) => {
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
          handleMessage(JSON.parse(jsonStr), agentId)
        } catch (e) {
          // 忽略解析失败
        }
      }
    }
  }

  const handleMessage = (msg, agentId) => {
    switch (msg.type) {
      case 'start':
        setThreadId(msg.thread_id)
        break
      case 'status':
        patchMessage(agentId, { status: msg.message })
        break
      case 'clarify':
        patchMessage(agentId, {
          status: '',
          text: msg.question,
          kind: 'clarify',
        })
        break
      case 'guide_start':
        patchMessage(agentId, { text: '', kind: 'guide' })
        break
      case 'guide_token':
        patchMessage(agentId, {
          text: (prev) => prev + msg.token,
        })
        break
      case 'done':
        if (msg.guide_markdown) {
          patchMessage(agentId, {
            text: msg.guide_markdown,
            kind: 'guide',
            status: '',
          })
        }
        break
      case 'error':
        patchMessage(agentId, { status: '', text: '出错：' + msg.message, kind: 'error' })
        break
      default:
        break
    }
  }

  // 提交输入：有追问进行中则 resume，否则新发起
  const onSubmit = () => {
    const content = input.trim()
    if (!content || loading) return
    // 判断是否有未完成的追问（最后一条 agent 消息是 clarify 类型）
    const last = messages[messages.length - 1]
    if (last && last.role === 'agent' && last.kind === 'clarify') {
      handleResume(content)
    } else {
      handlePlan(content)
    }
  }

  const pickTemplate = (text) => {
    setInput(text)
    inputRef.current?.focus()
  }

  const startNewChat = () => {
    setMessages([])
    setThreadId('')
    setInput('')
  }

  return (
    <div className="chat-app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">🧳</span>
          <div>
            <div className="brand-title">TripMind · 旅行规划</div>
            <div className="brand-sub">LangGraph · FastAPI · MCP</div>
          </div>
        </div>
        <div className="topbar-actions">
          <button className="ghost-btn" onClick={startNewChat} disabled={loading}>
            ✚ 新对话
          </button>
          <button className="ghost-btn" onClick={loadHistory} disabled={loading}>
            🕘 历史记录
          </button>
        </div>
      </header>

      <main className="chat-main">
        {/* 消息列表 */}
        <div className="msg-list" ref={listRef}>
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-logo">🧳</div>
              <h2>想去哪儿？</h2>
              <p>告诉我目的地、天数和预算，我来帮你规划行程</p>
              <div className="templates">
                {EXAMPLE_TEMPLATES.map((t) => (
                  <button
                    key={t.label}
                    className="chip"
                    onClick={() => pickTemplate(t.text)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`msg-row ${m.role}`}>
                <div className={`avatar ${m.role}`}>
                  {m.role === 'user' ? '🙂' : '🧳'}
                </div>
                <div className={`bubble ${m.role} ${m.kind || ''}`}>
                  {m.status && <div className="bubble-status">{m.status}</div>}
                  {m.text && m.kind === 'guide' ? (
                    <div className="markdown">
                      <ReactMarkdown>{m.text}</ReactMarkdown>
                    </div>
                  ) : m.text ? (
                    <div className="bubble-text">{m.text}</div>
                  ) : (
                    !m.status && <div className="typing"><span /><span /><span /></div>
                  )}
                  {m.kind === 'guide' && m.text && (
                    <div className="bubble-actions">
                      <button
                        className="mini-btn ghost"
                        onClick={() => {
                          const blob = new Blob([m.text], { type: 'text/markdown' })
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
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* 输入区 */}
        <div className="input-bar">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                onSubmit()
              }
            }}
            placeholder="输入旅行需求，例如：武汉出发，3天，预算3000…（Enter 发送，Shift+Enter 换行）"
            rows={1}
          />
          <button
            className="primary-btn send-btn"
            onClick={onSubmit}
            disabled={loading || !input.trim()}
          >
            {loading ? '…' : '发送'}
          </button>
        </div>
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
