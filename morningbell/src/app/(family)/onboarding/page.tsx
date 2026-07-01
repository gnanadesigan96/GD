'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card } from '@/components/ui/Card'
import { SERVICE_DEFINITIONS } from '@/constants/services'
import { TIMEZONES } from '@/constants/timezones'

const LANGUAGES = ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada']
const STEPS = ['About them', 'Type of care', 'Details']

const selectClass = 'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
const textareaClass = 'w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none'
const pillActive = 'bg-primary-700 text-white border-primary-700'
const pillInactive = 'bg-white text-slate-600 border-slate-200 hover:border-primary-400 hover:text-primary-700'

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
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Set up care for your loved one</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Takes about 3 minutes to complete</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
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

      {/* Step 1 */}
      {step === 1 && (
        <Card>
          <h3 className="text-base font-semibold text-slate-900 mb-5">About your loved one</h3>
          <div className="space-y-4">
            <Input id="name" label="Their name" value={elder.name} onChange={e => setElder(d => ({ ...d, name: e.target.value }))} placeholder="e.g. Mom, Dad, or their first name" />
            <Input id="age" type="number" label="Age" value={elder.age} onChange={e => setElder(d => ({ ...d, age: e.target.value }))} placeholder="75" />
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Their timezone</label>
              <select className={selectClass} value={elder.timezone} onChange={e => setElder(d => ({ ...d, timezone: e.target.value }))}>
                {TIMEZONES.map(tz => <option key={tz.value} value={tz.value}>{tz.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Their preferred language</label>
              <select className={selectClass} value={elder.language} onChange={e => setElder(d => ({ ...d, language: e.target.value }))}>
                {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Health notes <span className="text-slate-400 font-normal">(optional)</span></label>
              <textarea className={textareaClass} rows={3} placeholder="Any relevant health information the companion should know..." value={elder.healthNotes} onChange={e => setElder(d => ({ ...d, healthNotes: e.target.value }))} />
            </div>
            <Button onClick={() => setStep(2)} disabled={!elder.name || !elder.age} className="w-full">
              Continue
            </Button>
          </div>
        </Card>
      )}

      {/* Step 2 */}
      {step === 2 && (
        <Card>
          <h3 className="text-base font-semibold text-slate-900 mb-5">What kind of support do they need?</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
            {SERVICE_DEFINITIONS.map(svc => (
              <button key={svc.type} type="button" onClick={() => setServiceType(svc.type)}
                className={`p-4 rounded-xl border-2 text-left transition-all duration-150 cursor-pointer ${serviceType === svc.type ? 'border-primary-600 bg-primary-50' : 'border-slate-200 hover:border-primary-300 bg-white'}`}>
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${serviceType === svc.type ? 'bg-primary-100 text-primary-700' : 'bg-slate-100 text-slate-500'}`}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                  </svg>
                </div>
                <div className={`font-semibold text-sm ${serviceType === svc.type ? 'text-primary-700' : 'text-slate-900'}`}>{svc.label}</div>
                <div className="text-xs text-slate-500 mt-1 leading-relaxed">{svc.description}</div>
              </button>
            ))}
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)} disabled={!serviceType} className="flex-1">Continue</Button>
          </div>
        </Card>
      )}

      {/* Step 3 */}
      {step === 3 && selectedService && (
        <Card>
          <h3 className="text-base font-semibold text-slate-900 mb-5">{selectedService.label} — a few more details</h3>
          <div className="space-y-5">
            {selectedService.parameters.map(param => (
              <div key={param.key}>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  {param.label}{param.required && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                {param.type === 'select' && (
                  <select className={selectClass} value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)}>
                    <option value="">Select...</option>
                    {param.options?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                )}
                {param.type === 'multiselect' && (
                  <div className="flex flex-wrap gap-2">
                    {param.options?.map(opt => {
                      const selected = ((parameters[param.key] as string[]) || []).includes(opt)
                      return (
                        <button key={opt} type="button" onClick={() => toggleMulti(param.key, opt)}
                          className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all duration-150 cursor-pointer ${selected ? pillActive : pillInactive}`}>
                          {opt}
                        </button>
                      )
                    })}
                  </div>
                )}
                {param.type === 'text' && (
                  <input type="text" className={selectClass} placeholder={param.placeholder} value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
                {param.type === 'textarea' && (
                  <textarea className={textareaClass} rows={3} placeholder={param.placeholder} value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
                {param.type === 'time' && (
                  <input type="time" className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500" value={(parameters[param.key] as string) || ''} onChange={e => setParam(param.key, e.target.value)} />
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-6">
            <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
            <Button onClick={handleSubmit} className="flex-1" loading={loading}>Submit &amp; choose plan</Button>
          </div>
        </Card>
      )}
    </div>
  )
}
