'use client'
import { useState } from 'react'

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ta', label: 'தமிழ்' },
  { value: 'te', label: 'తెలుగు' },
  { value: 'hi', label: 'हिन्दी' },
  { value: 'kn', label: 'ಕನ್ನಡ' },
]

export function LanguageSwitcher() {
  const [lang, setLang] = useState('en')
  return (
    <select
      value={lang}
      onChange={e => setLang(e.target.value)}
      className="text-sm border border-gray-200 rounded-lg px-2 py-1 text-gray-700 focus:outline-none focus:ring-2 focus:ring-amber-500"
    >
      {LANGUAGES.map(l => (
        <option key={l.value} value={l.value}>{l.label}</option>
      ))}
    </select>
  )
}
