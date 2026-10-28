import { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import './layout.css'

function AppLayout() {
  const { pathname } = useLocation()
  const mainRef = useRef(null)
  const isFirstRender = useRef(true)

  // Start each page at the top, and move focus to the new page's content so
  // keyboard and screen-reader users land in the right place.
  useEffect(() => {
    window.scrollTo(0, 0)
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])

  function skipToContent(event) {
    // Focus directly instead of following "#main-content", which would push a
    // history entry and drop the router state.
    event.preventDefault()
    mainRef.current?.focus()
  }

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link" onClick={skipToContent}>Skip to content</a>
      <Sidebar />
      <main id="main-content" ref={mainRef} className="app-main" tabIndex={-1}>
        <div className="app-content">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default AppLayout
