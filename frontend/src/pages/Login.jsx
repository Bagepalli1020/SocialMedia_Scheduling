import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/dashboard" replace />

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="panel w-full max-w-md p-8 fade-up">
        <p className="brand-font text-2xl text-[var(--accent)]">PulseSchedule</p>
        <h1 className="mt-2 text-2xl">Welcome back</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">Sign in to manage scheduled posts for your organization.</p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Email</span>
            <input
              className="input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Password</span>
            <input
              className="input"
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
          <button className="btn btn-primary w-full" disabled={loading} type="submit">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-5 text-sm text-[var(--muted)]">
          New here?{' '}
          <Link className="font-semibold text-[var(--accent)]" to="/register">
            Create an organization
          </Link>
        </p>
      </div>
    </div>
  )
}
