'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { TIMEZONES } from '@/constants/timezones'

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ta', label: 'Tamil' },
  { value: 'te', label: 'Telugu' },
  { value: 'hi', label: 'Hindi' },
  { value: 'kn', label: 'Kannada' },
]

export default function RegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    language: 'en',
    timezone: 'America/New_York',
  })

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
    <div className="min-h-screen bg-amber-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl">🔔</span>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">Create your account</h1>
          <p className="text-sm text-gray-500 mt-1">For families — start your free 2-week trial</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input id="name" label="Full name" value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Jane Smith" required />
          <Input id="email" type="email" label="Email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="you@example.com" required />
          <Input id="password" type="password" label="Password (min 8 characters)" value={form.password} onChange={(e) => set('password', e.target.value)} placeholder="••••••••" required minLength={8} />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your timezone</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              value={form.timezone}
              onChange={(e) => set('timezone', e.target.value)}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>{tz.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preferred language</label>
            <select
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              value={form.language}
              onChange={(e) => set('language', e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" className="w-full" size="lg" loading={loading}>
            Create account
          </Button>
        </form>
        <p className="text-center text-sm text-gray-600 mt-4">
          Are you a companion?{' '}
          <Link href="/register/companion" className="text-amber-600 font-medium hover:underline">
            Apply here
          </Link>
        </p>
        <p className="text-center text-sm text-gray-600 mt-2">
          Already have an account?{' '}
          <Link href="/login" className="text-amber-600 font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
