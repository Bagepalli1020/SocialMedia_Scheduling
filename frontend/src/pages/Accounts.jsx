import { useEffect, useState } from 'react'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

const platforms = [
  { value: 'twitter', label: 'Twitter / X' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'linkedin', label: 'LinkedIn' },
]

export default function Accounts() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [accounts, setAccounts] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [form, setForm] = useState({
    platform: 'twitter',
    account_name: '',
    access_token: 'mock-token-demo',
  })

  async function load() {
    const { data } = await api.get('/social-accounts')
    setAccounts(data)
  }

  useEffect(() => {
    load().catch((err) => setError(err.response?.data?.detail || 'Failed to load accounts'))
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      await api.post('/social-accounts', form)
      setSuccess('Social account connected (mock token stored).')
      setForm((prev) => ({ ...prev, account_name: '' }))
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not connect account')
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Disconnect this account?')) return
    try {
      await api.delete(`/social-accounts/${id}`)
      await load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Delete failed')
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl">Social accounts</h1>
        <p className="mt-1 text-[var(--muted)]">
          Connect platform accounts for your organization. Mock access tokens are allowed for this assignment.
        </p>
      </div>

      {isAdmin ? (
        <form className="panel p-6 space-y-4 fade-up" onSubmit={handleCreate}>
          <h2 className="text-xl">Connect account</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Platform</span>
              <select
                className="input"
                value={form.platform}
                onChange={(e) => setForm((p) => ({ ...p, platform: e.target.value }))}
              >
                {platforms.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Account name</span>
              <input
                className="input"
                required
                value={form.account_name}
                onChange={(e) => setForm((p) => ({ ...p, account_name: e.target.value }))}
                placeholder="@brand"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium">Access token (mock OK)</span>
              <input
                className="input"
                required
                value={form.access_token}
                onChange={(e) => setForm((p) => ({ ...p, access_token: e.target.value }))}
                placeholder="mock-token"
              />
            </label>
          </div>
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
          {success && <p className="text-sm text-[var(--ok)]">{success}</p>}
          <button className="btn btn-primary" type="submit">
            Connect account
          </button>
        </form>
      ) : (
        <div className="panel p-5 text-sm text-[var(--muted)]">
          Only organization admins can connect or remove social accounts. You can still schedule posts to
          existing accounts.
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-xl">Connected accounts</h2>
        {accounts.length === 0 ? (
          <div className="panel p-6 text-sm text-[var(--muted)]">No accounts connected yet.</div>
        ) : (
          accounts.map((account) => (
            <article key={account.id} className="panel p-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold capitalize">{account.platform}</p>
                <p className="text-sm text-[var(--muted)]">
                  {account.account_name} · token {account.access_token_preview}
                </p>
              </div>
              {isAdmin && (
                <button
                  type="button"
                  className="btn btn-ghost text-sm text-[var(--danger)]"
                  onClick={() => handleDelete(account.id)}
                >
                  Disconnect
                </button>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  )
}
