'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { TIMEZONES } from '@/constants/timezones'

const BellIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
)
const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ta', label: 'Tamil' },
  { value: 'te', label: 'Telugu' },
  { value: 'hi', label: 'Hindi' },
  { value: 'kn', label: 'Kannada' },
]

const PERKS = [
  'Vetted, background-checked companions',
  'Daily reports straight to your inbox',
  'Cancel or pause anytime',
]

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', email: '', password: '', language: 'en', timezone: 'America/New_York' })

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, role: 'FAMILY' }),
    })
    setLoading(false)
    if (res.ok) {
      router.push('/login?registered=1')
    } else {
      const data = await res.json()
      setError(data.error || 'Registration failed')
    }
  }

  return (
    <div className="min-h-screen flex font-sans">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary-700 flex-col justify-between p-14">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center text-white">
            <BellIcon />
          </div>
          <span className="text-xl font-bold text-white">MorningBell</span>
        </div>

        <div>
          <p className="text-primary-200 text-sm font-semibold uppercase tracking-widest mb-4">Why families love us</p>
          <h2 className="text-white text-3xl font-bold leading-tight mb-8">
            A real human voice,<br />every single morning.
          </h2>
          <div className="space-y-4">
            {PERKS.map((perk) => (
              <div key={perk} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-white flex-shrink-0">
                  <CheckIcon />
                </div>
                <span className="text-white/85 text-sm">{perk}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="text-white/30 text-xs">© 2025 MorningBell. Not a medical provider.</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center px-8 py-16 bg-slate-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="w-9 h-9 bg-primary-700 rounded-lg flex items-center justify-center text-white">
              <BellIcon />
            </div>
            <span className="text-xl font-bold text-slate-900">MorningBell</span>
          </div>

          <div className="bg-white rounded-2xl border border-slate-100 shadow-card-lg p-8">
            <h1 className="text-2xl font-bold text-slate-900 mb-1 tracking-tight">Create your account</h1>
            <p className="text-slate-500 text-sm mb-8">For families · Start your free 2-week trial</p>

            <form onSubmit={handleSubmit} className="space-y-5">
              <Input id="name" label="Full name" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Jane Smith" required />
              <Input id="email" type="email" label="Email address" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="you@example.com" required />
              <Input id="password" type="password" label="Password" value={form.password} onChange={(e) => set('password', e.target.value)} placeholder="Min 8 characters" required minLength={8} />

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Your timezone</label>
                <select
                  className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  value={form.timezone}
                  onChange={(e) => set('timezone', e.target.value)}
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz.value} value={tz.value}>{tz.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Preferred language</label>
                <select
                  className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  value={form.language}
                  onChange={(e) => set('language', e.target.value)}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>{l.label}</option>
                  ))}
                </select>
              </div>

              {error && (
                <div className="flex items-center gap-2.5 bg-red-50 border border-red-100 text-red-700 text-sm rounded-lg px-4 py-3">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                    <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full" size="lg" loading={loading}>
                Create account
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-slate-100 space-y-3 text-center">
              <p className="text-sm text-slate-600">
                Are you a companion?{' '}
                <Link href="/register/companion" className="text-primary-700 font-semibold hover:text-primary-800 transition-colors">
                  Apply here
                </Link>
              </p>
              <p className="text-sm text-slate-600">
                Already have an account?{' '}
                <Link href="/login" className="text-primary-700 font-semibold hover:text-primary-800 transition-colors">
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
