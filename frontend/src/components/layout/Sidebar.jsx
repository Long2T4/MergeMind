import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getHealth } from '../../services/api'
import Icon from './Icon'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: 'home', isActive: (path) => path === '/' },
  { to: '/reviews/new', label: 'New Review', icon: 'code', isActive: (path) => path === '/reviews/new' },
  {
    to: '/history',
    label: 'History',
    icon: 'clock',
    // A saved review's results page belongs to History.
    isActive: (path) => path.startsWith('/history') || (path.startsWith('/reviews/') && path !== '/reviews/new'),
  },
  { to: '/learning', label: 'Learning', icon: 'trend', isActive: (path) => path.startsWith('/learning') },
  { to: '/projects', label: 'Projects', icon: 'folder', isActive: (path) => path.startsWith('/projects') },
]

const STATUS_TEXT = {
  checking: 'Checking API…',
  online: 'API online',
  offline: 'API unreachable',
}

function ApiStatus() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let active = true
    getHealth()
      .then((data) => { if (active) setStatus(data?.status === 'ok' ? 'online' : 'offline') })
      .catch(() => { if (active) setStatus('offline') })
    return () => { active = false }
  }, [])

  return (
    <p className={`api-status is-${status}`} role="status">
      <span className="status-dot" aria-hidden="true" />
      {STATUS_TEXT[status]}
    </p>
  )
}

function Sidebar() {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Close the mobile menu after navigating.
  useEffect(() => { setMenuOpen(false) }, [pathname])

  // Escape closes the open mobile menu.
  useEffect(() => {
    if (!menuOpen) return undefined
    function handleKey(event) {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [menuOpen])

  return (
    <header className={`sidebar ${menuOpen ? 'is-open' : ''}`}>
      <Link to="/" className="sidebar-brand" aria-label="MergeMind home">
        <span className="brand-mark"><Icon name="logo" size={20} strokeWidth={2} /></span>
        <span>MergeMind</span>
      </Link>

      <button
        type="button"
        className="menu-toggle btn btn-ghost btn-sm"
        aria-expanded={menuOpen}
        aria-controls="primary-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <Icon name={menuOpen ? 'close' : 'menu'} />
        <span className="sr-only">{menuOpen ? 'Close menu' : 'Open menu'}</span>
      </button>

      <div className="sidebar-panel" id="primary-navigation">
        <nav aria-label="Primary">
          <p className="sidebar-section-label eyebrow">Workspace</p>
          <ul className="nav-list">
            {NAV_ITEMS.map((item) => {
              const active = item.isActive(pathname)
              return (
                <li key={item.to}>
                  <Link to={item.to} className="nav-link" aria-current={active ? 'page' : undefined}>
                    <Icon name={item.icon} />
                    {item.label}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <ApiStatus />
        </div>
      </div>
    </header>
  )
}

export default Sidebar
