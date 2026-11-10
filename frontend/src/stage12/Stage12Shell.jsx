import { useEffect, useState } from 'react'
import { supabase } from './auth'
import { Stage12Panel } from './Stage12Panel'
import './stage12.css'

export default function Stage12Shell({ children }) {
  const [ready, setReady] = useState(false)
  const [session, setSession] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('sign-in')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!supabase) { setReady(true); return }
    let live = true
    supabase.auth.getSession().then(({ data, error }) => {
      if (!live) return
      if (error) setError(error.message)
      setSession(data?.session || null)
      setReady(true)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, updated) => {
      if (live) { setSession(updated); setReady(true) }
    })
    return () => { live = false; data.subscription.unsubscribe() }
  }, [])

  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const credentials = { email: email.trim(), password }
      const { data, error: authError } = mode === 'sign-in'
        ? await supabase.auth.signInWithPassword(credentials)
        : await supabase.auth.signUp(credentials)
      if (authError) throw authError
      if (mode === 'sign-up' && !data.session) setError('Check your email to confirm your account before signing in.')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  async function logout() {
    setError('')
    const { error: logoutError } = await supabase.auth.signOut()
    if (logoutError) setError(logoutError.message)
  }

  if (!ready) return <div className="s12-center">Checking your session…</div>
  if (!supabase) return <div className="s12-center s12-error">Stage 12 needs VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.</div>
  if (!session) return (
    <main className="s12-center">
      <form className="s12-login" onSubmit={submit}>
        <div className="s12-symbol">M</div>
        <h1>MergeMind</h1>
        <p>{mode === 'sign-in' ? 'Sign in to your private projects and reviews' : 'Create your developer account'}</p>
        <label>Email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
        <label>Password<input type="password" required minLength={6} autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'} value={password} onChange={e => setPassword(e.target.value)} /></label>
        {error && <p className="s12-error" role="alert">{error}</p>}
        <button type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'sign-in' ? 'Sign in' : 'Sign up'}</button>
        <button className="s12-link" type="button" onClick={() => { setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in'); setError('') }}>{mode === 'sign-in' ? 'Create an account' : 'Already have an account? Sign in'}</button>
      </form>
    </main>
  )
  return <>
    {children}
    <Stage12Panel session={session} onLogout={logout} />
  </>
}
