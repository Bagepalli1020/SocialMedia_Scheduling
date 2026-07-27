import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    organization_name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/dashboard" replace />

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
      navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="panel w-full max-w-md p-8 fade-up">
        <p className="brand-font text-2xl text-[var(--accent)]">PulseSchedule</p>
        <h1 className="mt-2 text-2xl">Create your workspace</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Registers a new organization (tenant) and makes you the admin.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Organization name</span>
            <input
              className="input"
              required
              value={form.organization_name}
              onChange={(e) => update('organization_name', e.target.value)}
              placeholder="Acme Marketing"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Work email</span>
            <input
              className="input"
              type="email"
              required
              value={form.email}
              onChange={(e) => update('email', e.target.value)}
              placeholder="admin@acme.com"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium">Password</span>
            <input
              className="input"
              type="password"
              required
              minLength={6}
              value={form.password}
              onChange={(e) => update('password', e.target.value)}
              placeholder="At least 6 characters"
            />
          </label>
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
          <button className="btn btn-primary w-full" disabled={loading} type="submit">
            {loading ? 'Creating…' : 'Create workspace'}
          </button>
        </form>

        <p className="mt-5 text-sm text-[var(--muted)]">
          Already have an account?{' '}
          <Link className="font-semibold text-[var(--accent)]" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
