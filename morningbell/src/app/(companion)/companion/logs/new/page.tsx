'use client'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

const CheckCircleIcon = () => (
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
  </svg>
)

const MOODS = [
  { label: 'Happy', value: 'Happy' },
  { label: 'Calm', value: 'Calm' },
  { label: 'Sad', value: 'Sad' },
  { label: 'Anxious', value: 'Anxious' },
  { label: 'Tired', value: 'Tired' },
  { label: 'Irritable', value: 'Irritable' },
]

const selectClass = 'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
const textareaClass = 'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none'

export default function NewLogPage() {
  const [assignments, setAssignments] = useState<any[]>([])
  const [form, setForm] = useState({ assignmentId: '', mood: '', medicationTaken: '', content: '', concerns: '' })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    fetch('/api/assignments/mine').then(r => r.json()).then(setAssignments)
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    await fetch('/api/logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        medicationTaken: form.medicationTaken === 'yes' ? true : form.medicationTaken === 'no' ? false : undefined,
      }),
    })
    setLoading(false)
    setSuccess(true)
    setForm({ assignmentId: '', mood: '', medicationTaken: '', content: '', concerns: '' })
  }

  if (success) {
    return (
      <div className="max-w-lg mx-auto">
        <Card className="text-center py-14">
          <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-500">
            <CheckCircleIcon />
          </div>
          <h2 className="text-base font-semibold text-slate-900">Log submitted</h2>
          <p className="text-slate-500 text-sm mt-1">The family has been notified.</p>
          <Button className="mt-6" onClick={() => setSuccess(false)}>Add another log</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Daily Log</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Record today's session for the family</p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Client */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Client</label>
            <select className={selectClass} value={form.assignmentId} onChange={e => setForm(f => ({ ...f, assignmentId: e.target.value }))} required>
              <option value="">Select client...</option>
              {assignments.map((a: any) => <option key={a.id} value={a.id}>{a.request?.elder?.name}</option>)}
            </select>
          </div>

          {/* Mood */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Client's mood today</label>
            <div className="flex flex-wrap gap-2">
              {MOODS.map(mood => (
                <button key={mood.value} type="button" onClick={() => setForm(f => ({ ...f, mood: mood.value }))}
                  className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all duration-150 cursor-pointer ${form.mood === mood.value ? 'bg-primary-700 text-white border-primary-700' : 'bg-white text-slate-600 border-slate-200 hover:border-primary-400 hover:text-primary-700'}`}>
                  {mood.label}
                </button>
              ))}
            </div>
          </div>

          {/* Medication */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Medication taken?</label>
            <div className="flex gap-2">
              {[{ label: 'Yes', value: 'yes' }, { label: 'No', value: 'no' }, { label: 'N/A', value: 'not applicable' }].map(opt => (
                <button key={opt.value} type="button" onClick={() => setForm(f => ({ ...f, medicationTaken: opt.value }))}
                  className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-150 cursor-pointer ${form.medicationTaken === opt.value ? (opt.value === 'yes' ? 'bg-emerald-600 text-white border-emerald-600' : opt.value === 'no' ? 'bg-red-500 text-white border-red-500' : 'bg-slate-500 text-white border-slate-500') : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-slate-100" />

          {/* Session summary */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Session summary <span className="text-red-400">*</span></label>
            <textarea className={textareaClass} rows={4} placeholder="How was the session? What did you discuss? Any notable moments or observations..." value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} required />
          </div>

          {/* Concerns */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Concerns <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <textarea className={textareaClass} rows={2} placeholder="Any health concerns or things the family should be aware of..." value={form.concerns} onChange={e => setForm(f => ({ ...f, concerns: e.target.value }))} />
          </div>

          <Button type="submit" className="w-full" size="lg" loading={loading}>
            Submit log
          </Button>
        </form>
      </Card>
    </div>
  )
}
