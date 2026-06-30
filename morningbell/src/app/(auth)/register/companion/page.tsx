'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

const LANGUAGES = ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada']
const SKILLS = ['Companionship', 'Medication tracking', 'Health monitoring', 'Activity coaching', 'Yoga', 'Music', 'Reading', 'Family coordination']
const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function CompanionRegisterPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    bio: '',
    languages: [] as string[],
    skills: [] as string[],
    availability: [] as { day: string; startTime: string; endTime: string }[],
  })

  function toggleItem(key: 'languages' | 'skills', item: string) {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(item) ? f[key].filter((i) => i !== item) : [...f[key], item],
    }))
  }

  function addAvailability(day: string) {
    if (form.availability.find((a) => a.day === day)) return
    setForm((f) => ({ ...f, availability: [...f.availability, { day, startTime: '09:00', endTime: '17:00' }] }))
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
      body: JSON.stringify({
        name: form.name,
        email: form.email,
        password: form.password,
        role: 'COMPANION',
        language: 'en',
        timezone: 'Asia/Kolkata',
        bio: form.bio,
        languages: form.languages,
        skills: form.skills,
        availability: form.availability,
      }),
    })
    setLoading(false)
    if (res.ok) router.push('/login?registered=companion')
    else {
      const data = await res.json()
      setError(data.error || 'Registration failed')
    }
  }

  return (
    <div className="min-h-screen bg-amber-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-lg">
        <div className="text-center mb-6">
          <span className="text-4xl">🤝</span>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">Apply as a Companion</h1>
          <p className="text-sm text-gray-500 mt-1">Step {step} of 3</p>
        </div>

        <form onSubmit={step < 3 ? (e) => { e.preventDefault(); setStep(s => s + 1) } : handleSubmit} className="space-y-4">
          {step === 1 && (
            <>
              <Input id="name" label="Full name" value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} required />
              <Input id="email" type="email" label="Email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))} required />
              <Input id="password" type="password" label="Password" value={form.password} onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))} required minLength={8} />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">About you</label>
                <textarea
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
                  rows={3}
                  placeholder="Brief introduction — your background, experience..."
                  value={form.bio}
                  onChange={(e) => setForm(f => ({ ...f, bio: e.target.value }))}
                />
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Languages you speak</label>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => toggleItem('languages', lang)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${form.languages.includes(lang) ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300 hover:border-amber-400'}`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Your skills</label>
                <div className="flex flex-wrap gap-2">
                  {SKILLS.map((skill) => (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggleItem('skills', skill)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${form.skills.includes(skill) ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300 hover:border-amber-400'}`}
                    >
                      {skill}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {step === 3 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Your availability (IST)</label>
              <div className="flex flex-wrap gap-2 mb-4">
                {DAYS.map((day) => (
                  <button
                    key={day}
                    type="button"
                    onClick={() => addAvailability(day)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${form.availability.find(a => a.day === day) ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300 hover:border-amber-400'}`}
                  >
                    {day.slice(0, 3)}
                  </button>
                ))}
              </div>
              {form.availability.map((slot) => (
                <div key={slot.day} className="flex items-center gap-3 mb-2 p-3 bg-amber-50 rounded-lg">
                  <span className="text-sm font-medium w-24">{slot.day}</span>
                  <input type="time" value={slot.startTime} onChange={(e) => updateAvailability(slot.day, 'startTime', e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-sm" />
                  <span className="text-sm text-gray-500">to</span>
                  <input type="time" value={slot.endTime} onChange={(e) => updateAvailability(slot.day, 'endTime', e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-sm" />
                </div>
              ))}
              <p className="text-xs text-gray-500 mt-2">⚠️ Your ID will be verified via Onfido before you can be assigned clients.</p>
            </div>
          )}

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex gap-3">
            {step > 1 && <Button type="button" variant="secondary" onClick={() => setStep(s => s - 1)}>Back</Button>}
            <Button type="submit" className="flex-1" loading={loading}>
              {step < 3 ? 'Continue' : 'Submit application'}
            </Button>
          </div>
        </form>

        <p className="text-center text-sm text-gray-600 mt-4">
          <Link href="/login" className="text-amber-600 font-medium hover:underline">Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}
