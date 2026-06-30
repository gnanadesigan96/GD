'use client'
import { useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const BellIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
)
const StarIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
)

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const result = await signIn('credentials', { email, password, redirect: false })
    setLoading(false)
    if (result?.error) {
      setError('Invalid email or password')
    } else {
      router.push('/dashboard')
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
          <div className="flex text-accent-400 mb-6">
            {[...Array(5)].map((_, i) => <StarIcon key={i} />)}
          </div>
          <blockquote className="text-white/90 text-2xl font-light leading-relaxed italic mb-8">
            "I wake up every morning knowing someone wonderful is there for my mother. That peace of mind is priceless."
          </blockquote>
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-white/20 rounded-full flex items-center justify-center text-white font-semibold text-sm">PS</div>
            <div>
              <p className="text-white font-semibold text-sm">Priya S.</p>
              <p className="text-white/50 text-xs">Family member · San Jose, CA</p>
            </div>
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
            <h1 className="text-2xl font-bold text-slate-900 mb-1 tracking-tight">Welcome back</h1>
            <p className="text-slate-500 text-sm mb-8">Sign in to your MorningBell account</p>

            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                id="email"
                type="email"
                label="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
              <div>
                <Input
                  id="password"
                  type="password"
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
                <div className="flex justify-end mt-2">
                  <button type="button" className="text-xs text-primary-600 hover:text-primary-800 transition-colors cursor-pointer font-medium">
                    Forgot password?
                  </button>
                </div>
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
                Sign in
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-slate-100 text-center">
              <p className="text-sm text-slate-600">
                New to MorningBell?{' '}
                <Link href="/register" className="text-primary-700 font-semibold hover:text-primary-800 transition-colors cursor-pointer">
                  Create an account
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
