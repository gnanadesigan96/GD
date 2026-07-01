'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'

const ROLES = ['Support', 'Operations Lead', 'Quality Reviewer', 'Clinical Advisor', 'Finance']

export default function TeamInviteForm() {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('Support')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const res = await fetch('/api/admin/team', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, role }),
    })
    setLoading(false)
    if (res.ok) {
      setSent(true)
      setEmail('')
      setRole('Support')
    } else {
      const data = await res.json()
      setError(data.error || 'Failed to send invite')
    }
  }

  if (sent) {
    return (
      <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3">
        <div className="w-8 h-8 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-emerald-800">Invite sent!</p>
          <p className="text-xs text-emerald-600">Team member will appear in the list above once they accept.</p>
        </div>
        <button onClick={() => setSent(false)} className="ml-auto text-xs text-emerald-700 hover:text-emerald-900 font-medium cursor-pointer">
          Invite another
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
      <input
        type="email"
        placeholder="colleague@company.com"
        value={email}
        onChange={e => setEmail(e.target.value)}
        required
        className="flex-1 rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
      />
      <select
        value={role}
        onChange={e => setRole(e.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
      >
        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      <Button type="submit" loading={loading}>Send invite</Button>
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </form>
  )
}
