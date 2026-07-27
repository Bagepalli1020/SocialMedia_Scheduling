import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

function Stat({ label, value }) {
  return (
    <div className="panel p-5 fade-up">
      <p className="text-sm text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api
      .get('/analytics/dashboard')
      .then(({ data }) => {
        if (active) setStats(data)
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.detail || 'Failed to load analytics')
      })
    return () => {
      active = false
    }
  }, [])

  if (error) {
    return <p className="text-[var(--danger)]">{error}</p>
  }

  if (!stats) {
    return <p className="text-[var(--muted)]">Loading analytics…</p>
  }

  const maxTrend = Math.max(1, ...stats.trends.map((t) => t.views + t.likes + t.shares))

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl">Analytics dashboard</h1>
          <p className="mt-1 text-[var(--muted)]">
            Organization-level engagement across scheduled and published posts.
          </p>
        </div>
        <Link to="/posts" className="btn btn-primary">
          Schedule a post
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total posts" value={stats.total_posts} />
        <Stat label="Scheduled" value={stats.scheduled_posts} />
        <Stat label="Published" value={stats.published_posts} />
        <Stat label="Failed" value={stats.failed_posts} />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Total views" value={stats.total_views} />
        <Stat label="Total likes" value={stats.total_likes} />
        <Stat label="Total shares" value={stats.total_shares} />
      </div>

      <section className="panel p-6">
        <h2 className="text-xl">Performance trends</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">Engagement grouped by scheduled date.</p>

        {stats.trends.length === 0 ? (
          <p className="mt-6 text-sm text-[var(--muted)]">
            No posts yet. Connect an account and schedule content to see trends.
          </p>
        ) : (
          <div className="mt-6 space-y-3">
            {stats.trends.map((t) => {
              const total = t.views + t.likes + t.shares
              const width = `${Math.max(6, (total / maxTrend) * 100)}%`
              return (
                <div key={t.date}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="font-medium">{t.date}</span>
                    <span className="text-[var(--muted)]">
                      {t.posts} posts · {t.views} views · {t.likes} likes · {t.shares} shares
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--accent-soft)] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
                      style={{ width }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
