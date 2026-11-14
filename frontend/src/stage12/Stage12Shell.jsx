import { useEffect, useMemo, useState } from 'react'
import { accountRequest, supabase } from './auth'
import { AccountContext } from './AccountContext'
import './stage12.css'

export default function Stage12Shell({ children }) {
  const [ready, setReady] = useState(false)
  const [session, setSession] = useState(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState('sign-in')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  // After sign-in, check once that the server can open this account.
  const [account, setAccount] = useState({ status: 'idle' })
  const userId = session?.user?.id
  const userEmail = session?.user?.email || ''

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

  useEffect(() => {
    if (!userId) { setAccount({ status: 'idle' }); return undefined }
    let live = true
    setAccount({ status: 'checking' })
    accountRequest('/me')
      .then(() => { if (live) setAccount({ status: 'ready' }) })
      .catch((err) => {
        if (!live) return
        // 409: saved data under this email must be linked by an administrator.
        // 403: the sign-in has no verified email. Other failures (server down)
        // are reported by each page, as before.
        if (err.status === 409 || err.status === 403) setAccount({ status: 'blocked', code: err.status, message: err.message })
        else setAccount({ status: 'ready' })
      })
    return () => { live = false }
  }, [userId])

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

  const accountValue = useMemo(() => ({ email: userEmail, logout }), [userEmail])

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
  if (account.status === 'idle' || account.status === 'checking') return <div className="s12-center" role="status">Opening your account…</div>
  if (account.status === 'blocked') return (
    <main className="s12-center">
      <section className="s12-login" aria-labelledby="account-blocked-title">
        <div className="s12-symbol">M</div>
        <h1 id="account-blocked-title">
          {account.code === 409 ? 'This account needs to be linked' : 'This account can’t be opened'}
        </h1>
        <p role="alert">
          {account.code === 409
            ? 'MergeMind already has saved reviews under this email. An administrator must link them to your sign-in before you can continue. Your saved data has not been changed.'
            : account.message}
        </p>
        <p>Signed in as <strong>{userEmail}</strong></p>
        {error && <p className="s12-error" role="alert">{error}</p>}
        <button type="button" onClick={logout}>Log out</button>
      </section>
    </main>
  )
  return <AccountContext.Provider value={accountValue}>{children}</AccountContext.Provider>
}
