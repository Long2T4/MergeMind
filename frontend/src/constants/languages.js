// Language values stored in code_reviews.programming_language.
// Shared by the submit form and the History filter so the two can't drift apart.
export const LANGUAGES = ['python', 'javascript', 'java', 'c', 'cpp', 'other']

export const LANGUAGE_LABELS = {
  python: 'Python',
  javascript: 'JavaScript',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  other: 'Other',
}

// Two- or three-letter tags used in compact lists (the "PY" / "JS" chips).
export const LANGUAGE_SHORT = {
  python: 'PY',
  javascript: 'JS',
  java: 'JV',
  c: 'C',
  cpp: 'C++',
  other: '··',
}

// File extension shown on the editor tab for each language.
export const LANGUAGE_EXTENSIONS = {
  python: 'py',
  javascript: 'js',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  other: 'txt',
}

// Uploaded file extension -> stored language value.
const EXTENSION_TO_LANGUAGE = {
  py: 'python',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  java: 'java',
  c: 'c',
  h: 'c',
  cpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  hpp: 'cpp',
  hh: 'cpp',
}

export function languageFromFileName(fileName) {
  const extension = String(fileName || '').split('.').pop().toLowerCase()
  return EXTENSION_TO_LANGUAGE[extension] || null
}

export function languageLabel(language) {
  return LANGUAGE_LABELS[language] ?? language
}
