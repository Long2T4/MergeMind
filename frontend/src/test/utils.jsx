import { render } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import App from '../App'
import { ROUTER_FUTURE } from '../routerFuture'

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}{location.search}</output>
}

// Renders the whole app (layout + routes) at `route`, which may be a path
// or a { pathname, state } entry.
export function renderApp(route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]} future={ROUTER_FUTURE}>
      <App />
      <LocationProbe />
    </MemoryRouter>,
  )
}
