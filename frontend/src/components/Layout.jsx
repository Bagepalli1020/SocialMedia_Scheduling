import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/posts', label: 'Posts' },
  { to: '/accounts', label: 'Accounts' },
]

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-white/80 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <div>
              <div className="brand-font text-xl tracking-tight text-[var(--accent)]">PulseSchedule</div>
              <div className="text-xs text-[var(--muted)]">
                {user?.organization?.name || 'Organization'} · {user?.role}
              </div>
            </div>
            <nav className="hidden sm:flex items-center gap-1">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-2 text-sm font-medium transition ${
                      isActive
                        ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                        : 'text-[var(--muted)] hover:text-[var(--ink)]'
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden md:inline text-sm text-[var(--muted)]">{user?.email}</span>
            <button type="button" className="btn btn-ghost text-sm" onClick={logout}>
              Log out
            </button>
          </div>
        </div>
        <nav className="sm:hidden flex gap-1 px-4 pb-3 overflow-x-auto">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap ${
                  isActive
                    ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                    : 'text-[var(--muted)]'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
