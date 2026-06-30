'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { SERVICE_DEFINITIONS } from '@/constants/services'
import { TIMEZONES } from '@/constants/timezones'

const LANGUAGES = ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada']

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [elder, setElder] = useState({ name: '', age: '', language: 'English', timezone: 'America/New_York', healthNotes: '' })
  const [serviceType, setServiceType] = useState('')
  const [parameters, setParameters] = useState<Record<string, string | string[]>>({})

  const selectedService = SERVICE_DEFINITIONS.find(s => s.type === serviceType)

  function setParam(key: string, value: string | string[]) {
    setParameters(p => ({ ...p, [key]: value }))
  }

  function toggleMulti(key: string, value: string) {
    const current = (parameters[key] as string[]) || []
    setParam(key, current.includes(value) ? current.filter(v => v !== value) : [...current, value])
  }

  async function handleSubmit() {
    setLoading(true)
    const elderRes = await fetch('/api/elders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...elder, age: parseInt(elder.age) }),
    })
    const elderData = await elderRes.json()

    await fetch('/api/service-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ elderId: elderData.id, serviceType, parameters }),
    })
    setLoading(false)
    router.push('/subscription')
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Set up care for your loved one</h2>
        <p className="text-gray-600 mt-1">Step {step} of 3</p>
      </div>

      {step === 1 && (
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">About your loved one</h3>
          <div className="space-y-4">
            <Input id="name" label="Their name" value={elder.name} onChange={e => setElder(d => ({ ...d, name: e.target.value }))} placeholder="e.g. Mom, Dad, or their first name" />
            <Input id="age" type="number" label="Age" value={elder.age} onChange={e => setElder(d => ({ ...d, age: e.target.value }))} placeholder="75" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Their timezone</label>
              <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" value={elder.timezone} onChange={e => setElder(d => ({ ...d, timezone: e.target.value }))}>
                {TIMEZONES.map(tz => <option key={tz.value} value={tz.value}>{tz.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Their preferred language</label>
              <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" value={elder.language} onChange={e => setElder(d => ({ ...d, language: e.target.value }))}>
                {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Health notes (optional)</label>
              <textarea className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" rows={3} placeholder="Any relevant health information the companion should know..." value={elder.healthNotes} onChange={e => setElder(d => ({ ...d, healthNotes: e.target.value }))} />
            </div>
            <Button onClick={() => setStep(2)} disabled={!elder.name || !elder.age} className="w-full">Continue</Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">What kind of support do they need?</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SERVICE_DEFINITIONS.map(svc => (
              <button key={svc.type} type="button" onClick={() => setServiceType(svc.type)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${serviceType === svc.type ? 'border-amber-500 bg-amber-50' : 'border-gray-200 hover:border-amber-300'}`}>
                <div className="text-2xl mb-2">{svc.icon}</div>
                <div className="font-semibold text-gray-900">{svc.label}</div>
                <div className="text-xs text-gray-600 mt-1">{svc.description}</div>
              </button>
            ))}
          </div>
          <div className="flex gap-3 mt-4">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)} disabled={!serviceType} className="flex-1">Continue</Button>
          </div>
        </Card>
      )}

      {step === 3 && selectedService && (
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">{selectedService.icon} {selectedService.label} details</h3>
          <div className="space-y-4">
            {selectedService.parameters.map(param => (
              <div key={param.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{param.label}{param.required && ' *'}</label>
                {param.type === 'select' && (
                  <select className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)}>
                    <option value="">Select...</option>
                    {param.options?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                )}
                {param.type === 'multiselect' && (
                  <div className="flex flex-wrap gap-2">
                    {param.options?.map(opt => (
                      <button key={opt} type="button" onClick={() => toggleMulti(param.key, opt)}
                        className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${((parameters[param.key] as string[]) || []).includes(opt) ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-300'}`}>
                        {opt}
                      </button>
                    ))}
                  </div>
                )}
                {param.type === 'text' && (
                  <input type="text" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" placeholder={param.placeholder} value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
                {param.type === 'textarea' && (
                  <textarea className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" rows={3} placeholder={param.placeholder} value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
                {param.type === 'time' && (
                  <input type="time" className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-amber-500" value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-4">
            <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
            <Button onClick={handleSubmit} className="flex-1" loading={loading}>Submit & choose plan</Button>
          </div>
        </Card>
      )}
    </div>
  )
}
