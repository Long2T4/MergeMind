import { useState } from 'react'
import { LANGUAGES } from '../constants/languages'

function CodeSubmitForm({ onSubmit, isSubmitting }) {
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')

  function handleSubmit(event) {
    event.preventDefault()
    if (!code.trim()) return
    onSubmit({ code, language })
    setCode('')
  }

  return (
    <form className="code-submit-form" onSubmit={handleSubmit}>
      <label htmlFor="language-select">Language</label>
      <select
        id="language-select"
        value={language}
        onChange={(event) => setLanguage(event.target.value)}
      >
        {LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>

      <label htmlFor="code-input">Paste your code</label>
      <textarea
        id="code-input"
        rows={12}
        value={code}
        onChange={(event) => setCode(event.target.value)}
        placeholder="Paste your code here..."
      />

      <button type="submit" disabled={isSubmitting || !code.trim()}>
        {isSubmitting ? 'Submitting...' : 'Review Code'}
      </button>
    </form>
  )
}

export default CodeSubmitForm
