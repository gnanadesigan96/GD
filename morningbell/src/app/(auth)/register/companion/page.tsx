'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const BellIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
)

const LANGUAGES = ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada']
const SKILLS = ['Companionship', 'Medication tracking', 'Health monitoring', 'Activity coaching', 'Yoga', 'Music', 'Reading', 'Family coordination']
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const STEPS = ['Account', 'Skills', 'Availability']

export default function CompanionRegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    name: '', email: '', password: '', bio: '',
    languages: [] as string[], skills: [] as string[],
    availability: [] as { day: string; startTime: string; endTime: string }[],
  })

  function toggleItem(key: 'languages' | 'skills', item: string) {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(item) ? f[key].filter((i) => i !== item) : [...f[key], item],
    }))
  }

  function addAvailability(day: string) {
    if (form.availability.find((a) => a.day === day)) {
      setForm((f) => ({ ...f, availability: f.availability.filter((a) => a.day !== day) }))
    } else {
      setForm((f) => ({ ...f, availability: [...f.availability, { day, startTime: '09:00', endTime: '17:00' }] }))
    }
  }

  function updateAvailability(day: string, field: 'startTime' | 'endTime', value: string) {
    setForm((f) => ({
      ...f,
      availability: f.availability.map((a) => (a.day === day ? { ...a, [field]: value } : a)),
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: form.name, email: form.email, password: form.password, role: 'COMPANION', language: 'en', timezone: 'Asia/Kolkata', bio: form.bio, languages: form.languages, skills: form.skills, availability: form.availability }),
    })
    setLoading(false)
    if (res.ok) router.push('/login?registered=companion')
    else {
      const data = await res.json()
      setError(data.error || 'Registration failed')
    }
  }

  function advance(e: React.FormEvent) {
    e.preventDefault()
    setStep((s) => s + 1)
  }

  return (
    <div className="min-h-screen flex font-sans">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-5/12 bg-primary-700 flex-col justify-between p-14">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center text-white">
            <BellIcon />
          </div>
          <span className="text-xl font-bold text-white">MorningBell</span>
        </div>
        <div>
          <p className="text-primary-200 text-sm font-semibold uppercase tracking-widest mb-4">Become a companion</p>
          <h2 className="text-white text-3xl font-bold leading-tight mb-4">Make a difference<br />in someone's morning.</h2>
          <p className="text-white/70 text-sm leading-relaxed">Our companions are verified, trained, and matched with elderly clients for daily wellness check-ins — a meaningful way to earn while doing good.</p>
        </div>
        <p className="text-white/30 text-xs">© 2025 MorningBell. Not a medical provider.</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center px-8 py-16 bg-slate-50">
        <div className="w-full max-w-lg">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10">
            <div className="w-9 h-9 bg-primary-700 rounded-lg flex items-center justify-center text-white">
              <BellIcon />
            </div>
            <span className="text-xl font-bold text-slate-900">MorningBell</span>
          </div>

          <div className="bg-white rounded-2xl border border-slate-100 shadow-card-lg p-8">
            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-8">
              {STEPS.map((label, i) => {
                const n = i + 1
                const done = step > n
                const active = step === n
                return (
                  <div key={label} className="flex items-center gap-2 flex-1 last:flex-none">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all ${done ? 'bg-emerald-500 text-white' : active ? 'bg-primary-700 text-white' : 'bg-slate-100 text-slate-400'}`}>
                      {done ? (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                      ) : n}
                    </div>
                    <span className={`text-xs font-medium hidden sm:inline ${active ? 'text-slate-900' : 'text-slate-400'}`}>{label}</span>
                    {i < STEPS.length - 1 && <div className={`h-px flex-1 mx-1 ${done ? 'bg-emerald-300' : 'bg-slate-200'}`} />}
                  </div>
                )
              })}
            </div>

            <h1 className="text-xl font-bold text-slate-900 mb-1 tracking-tight">
              {step === 1 && 'Your account'}
              {step === 2 && 'Languages & skills'}
              {step === 3 && 'Availability'}
            </h1>
            <p className="text-slate-500 text-sm mb-6">
              {step === 1 && 'Create your companion login'}
              {step === 2 && 'Help us match you with the right clients'}
              {step === 3 && 'Set your weekly working hours (IST)'}
            </p>

            <form onSubmit={step < 3 ? advance : handleSubmit} className="space-y-5">
              {step === 1 && (
                <>
                  <Input id="name" label="Full name" value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Your full name" required />
                  <Input id="email" type="email" label="Email address" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} placeholder="you@example.com" required />
                  <Input id="password" type="password" label="Password" value={form.password} onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Min 8 characters" required minLength={8} />
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">About you</label>
                    <textarea
                      className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none"
                      rows={3}
                      placeholder="Your background, experience with elders, why you want to be a companion..."
                      value={form.bio}
                      onChange={(e) => setForm(f => ({ ...f, bio: e.target.value }))}
                    />
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Languages you speak</label>
                    <div className="flex flex-wrap gap-2">
                      {LANGUAGES.map((lang) => (
                        <button key={lang} type="button" onClick={() => toggleItem('languages', lang)}
                          className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all duration-150 cursor-pointer ${form.languages.includes(lang) ? 'bg-primary-700 text-white border-primary-700' : 'bg-white text-slate-600 border-slate-200 hover:border-primary-400 hover:text-primary-700'}`}>
                          {lang}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Your skills</label>
                    <div className="flex flex-wrap gap-2">
                      {SKILLS.map((skill) => (
                        <button key={skill} type="button" onClick={() => toggleItem('skills', skill)}
                          className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all duration-150 cursor-pointer ${form.skills.includes(skill) ? 'bg-primary-700 text-white border-primary-700' : 'bg-white text-slate-600 border-slate-200 hover:border-primary-400 hover:text-primary-700'}`}>
                          {skill}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {step === 3 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Select days you're available</label>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {DAYS.map((day) => (
                      <button key={day} type="button" onClick={() => addAvailability(day)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-150 cursor-pointer ${form.availability.find(a => a.day === day) ? 'bg-primary-700 text-white border-primary-700' : 'bg-white text-slate-600 border-slate-200 hover:border-primary-400'}`}>
                        {day.slice(0, 3)}
                      </button>
                    ))}
                  </div>
                  {form.availability.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {form.availability.map((slot) => (
                        <div key={slot.day} className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-100 rounded-lg">
                          <span className="text-sm font-semibold text-slate-700 w-24">{slot.day}</span>
                          <input type="time" value={slot.startTime} onChange={(e) => updateAvailability(slot.day, 'startTime', e.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500" />
                          <span className="text-sm text-slate-400">to</span>
                          <input type="time" value={slot.endTime} onChange={(e) => updateAvailability(slot.day, 'endTime', e.target.value)} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500" />
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex items-start gap-2 p-3 bg-primary-50 rounded-lg border border-primary-100">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary-600 flex-shrink-0 mt-0.5">
                      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <p className="text-xs text-primary-700 leading-relaxed">Your identity will be verified via Onfido before you can be assigned clients. This keeps our platform safe for everyone.</p>
                  </div>
                </div>
              )}

              {error && (
                <div className="flex items-center gap-2.5 bg-red-50 border border-red-100 text-red-700 text-sm rounded-lg px-4 py-3">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                    <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                  {error}
                </div>
              )}

              <div className="flex gap-3 pt-1">
                {step > 1 && (
                  <Button type="button" variant="secondary" onClick={() => setStep(s => s - 1)}>Back</Button>
                )}
                <Button type="submit" className="flex-1" loading={loading}>
                  {step < 3 ? 'Continue' : 'Submit application'}
                </Button>
              </div>
            </form>

            <div className="mt-6 pt-6 border-t border-slate-100 text-center">
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
