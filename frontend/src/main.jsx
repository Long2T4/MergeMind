import Stage12Shell from './stage12/Stage12Shell'
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
      <Stage12Shell><App /></Stage12Shell>
    </BrowserRouter>
  </React.StrictMode>,
)
