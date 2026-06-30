'use client'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

const MOODS = ['😊 Happy', '😌 Calm', '😔 Sad', '😰 Anxious', '😴 Tired', '😤 Irritable']

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
      <Card className="text-center py-12">
        <span className="text-5xl">✅</span>
        <h2 className="text-xl font-semibold text-gray-900 mt-4">Log submitted!</h2>
        <p className="text-gray-600 mt-2">The family has been notified.</p>
        <Button className="mt-6" onClick={() => setSuccess(false)}>Add another log</Button>
      </Card>
    )
  }

  return (
    <div className="max-w-xl space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Daily Log</h2>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client</label>
            <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" value={form.assignmentId} onChange={e => setForm(f => ({ ...f, assignmentId: e.target.value }))} required>
              <option value="">Select client...</option>
              {assignments.map((a: any) => <option key={a.id} value={a.id}>{a.request?.elder?.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Today's mood</label>
            <div className="flex flex-wrap gap-2">
              {MOODS.map(mood => (
                <button key={mood} type="button" onClick={() => setForm(f => ({ ...f, mood }))}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${form.mood === mood ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300'}`}>
                  {mood}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Medication taken?</label>
            <div className="flex gap-3">
              {['yes', 'no', 'not applicable'].map(opt => (
                <button key={opt} type="button" onClick={() => setForm(f => ({ ...f, medicationTaken: opt }))}
                  className={`px-4 py-2 rounded-lg text-sm border capitalize ${form.medicationTaken === opt ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300'}`}>
                  {opt}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Session summary</label>
            <textarea className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" rows={4} placeholder="How was the session? What did you discuss? Any notable moments..." value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Concerns (optional)</label>
            <textarea className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" rows={2} placeholder="Any health concerns or things the family should know..." value={form.concerns} onChange={e => setForm(f => ({ ...f, concerns: e.target.value }))} />
          </div>
          <Button type="submit" className="w-full" size="lg" loading={loading}>Submit log</Button>
        </form>
      </Card>
    </div>
  )
}
