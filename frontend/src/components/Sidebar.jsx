import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, KeyRound, Users, Bell, RefreshCw } from 'lucide-react'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/keywords', label: 'Keywords', icon: KeyRound },
  { to: '/competitors', label: 'Competidores', icon: Users },
  { to: '/alerts', label: 'Alertas', icon: Bell },
]

const styles = {
  sidebar: {
    width: 220,
    minHeight: '100vh',
    background: '#161b27',
    borderRight: '1px solid #1e2636',
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 0',
    flexShrink: 0,
  },
  logo: {
    padding: '0 20px 28px',
    fontSize: 18,
    fontWeight: 700,
    color: '#60a5fa',
    letterSpacing: '-0.02em',
  },
  nav: { display: 'flex', flexDirection: 'column', gap: 2 },
  link: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 20px',
    fontSize: 14,
    color: '#94a3b8',
    textDecoration: 'none',
    borderRadius: 8,
    margin: '0 8px',
    transition: 'background 0.15s, color 0.15s',
  },
  active: {
    background: '#1e3a5f',
    color: '#60a5fa',
  },
}

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>RankTracker</div>
      <nav style={styles.nav}>
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              ...styles.link,
              ...(isActive ? styles.active : {}),
            })}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
