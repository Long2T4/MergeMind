import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// Base styles first, so component and page stylesheets (imported by App) override them.
import './index.css'
import App from './App.jsx'
import { ROUTER_FUTURE } from './routerFuture'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter future={ROUTER_FUTURE}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
