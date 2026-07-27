import { useEffect, useMemo, useState } from 'react'
import api from '../api/client'

function toLocalInputValue(date = new Date(Date.now() + 60 * 60 * 1000)) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}

export default function Posts() {
  const [posts, setPosts] = useState([])
  const [accounts, setAccounts] = useState([])
  const [filter, setFilter] = useState('')
  const [logs, setLogs] = useState([])
  const [selectedPostId, setSelectedPostId] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState({
    content: '',
    scheduled_time: toLocalInputValue(),
    social_account_id: '',
  })

  async function load() {
    const params = filter ? { status: filter } : undefined
    const [postsRes, accountsRes] = await Promise.all([
      api.get('/posts', { params }),
      api.get('/social-accounts'),
    ])
    setPosts(postsRes.data)
    setAccounts(accountsRes.data)
    if (!form.social_account_id && accountsRes.data[0]) {
      setForm((prev) => ({ ...prev, social_account_id: String(accountsRes.data[0].id) }))
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err.response?.data?.detail || 'Failed to load posts'))
  }, [filter])

  const accountOptions = useMemo(() => accounts, [accounts])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.post('/posts', {
        content: form.content,
        social_account_id: Number(form.social_account_id),
        scheduled_time: new Date(form.scheduled_time).toISOString(),
      })
      setSuccess('Post scheduled successfully. The background worker will publish it when due.')
      setForm((prev) => ({ ...prev, content: '', scheduled_time: toLocalInputValue() }))
      await load()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(', '))
      } else {
        setError(detail || 'Could not schedule post')
      }
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this post?')) return
    await api.delete(`/posts/${id}`)
    if (selectedPostId === id) {
      setSelectedPostId(null)
      setLogs([])
    }
    await load()
  }

  async function showLogs(id) {
    setSelectedPostId(id)
    const { data } = await api.get(`/posts/${id}/logs`)
    setLogs(data)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl">Scheduled posts</h1>
        <p className="mt-1 text-[var(--muted)]">
          Create future posts. Celery workers publish them automatically at the scheduled time.
        </p>
      </div>

      <form className="panel p-6 space-y-4 fade-up" onSubmit={handleCreate}>
        <h2 className="text-xl">Schedule new post</h2>
        {accountOptions.length === 0 && (
          <p className="text-sm text-[var(--warn)]">
            Connect a social account first (Accounts page). Admins can add accounts.
          </p>
        )}
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Content</span>
          <textarea
            className="input min-h-28"
            required
            maxLength={5000}
            value={form.content}
            onChange={(e) => setForm((p) => ({ ...p, content: e.target.value }))}
            placeholder="What do you want to publish?"
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Social account</span>
            <select
              className="input"
              required
              value={form.social_account_id}
              onChange={(e) => setForm((p) => ({ ...p, social_account_id: e.target.value }))}
            >
              <option value="" disabled>
                Select account
              </option>
              {accountOptions.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.platform} · {a.account_name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Scheduled time</span>
            <input
              className="input"
              type="datetime-local"
              required
              value={form.scheduled_time}
              onChange={(e) => setForm((p) => ({ ...p, scheduled_time: e.target.value }))}
            />
          </label>
        </div>
        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
        {success && <p className="text-sm text-[var(--ok)]">{success}</p>}
        <button className="btn btn-primary" type="submit" disabled={!accountOptions.length}>
          Schedule post
        </button>
      </form>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl">Your posts</h2>
          <select className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="publishing">Publishing</option>
            <option value="published">Published</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {posts.length === 0 ? (
          <div className="panel p-6 text-sm text-[var(--muted)]">No posts yet.</div>
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <article key={post.id} className="panel p-5 fade-up">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={post.status} />
                      <span className="text-sm text-[var(--muted)]">
                        {post.platform} · {post.account_name}
                      </span>
                    </div>
                    <p className="mt-3 whitespace-pre-wrap">{post.content}</p>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      Scheduled: {new Date(post.scheduled_time).toLocaleString()}
                      {post.retry_count > 0 ? ` · Retries: ${post.retry_count}` : ''}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" className="btn btn-ghost text-sm" onClick={() => showLogs(post.id)}>
                      Logs
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost text-sm text-[var(--danger)]"
                      onClick={() => handleDelete(post.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
                {selectedPostId === post.id && (
                  <div className="mt-4 rounded-xl bg-[var(--surface)] p-4">
                    <h3 className="font-semibold">Publish logs</h3>
                    {logs.length === 0 ? (
                      <p className="mt-2 text-sm text-[var(--muted)]">No logs yet.</p>
                    ) : (
                      <ul className="mt-2 space-y-2 text-sm">
                        {logs.map((log) => (
                          <li key={log.id} className="border-b border-[var(--line)] pb-2">
                            <span className="font-medium">{log.status}</span>
                            <span className="text-[var(--muted)]">
                              {' '}
                              · {new Date(log.executed_at).toLocaleString()}
                            </span>
                            <p className="text-[var(--muted)]">{log.response}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
