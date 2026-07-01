import { prisma } from '@/lib/prisma'
import { notFound } from 'next/navigation'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

const PLAN_PRICES: Record<string, number> = { COMPANION: 99, CARETAKER: 199, PREMIUM: 349 }
const PLAN_COLORS: Record<string, string> = {
  COMPANION: 'bg-primary-50 text-primary-700',
  CARETAKER: 'bg-violet-50 text-violet-700',
  PREMIUM: 'bg-amber-50 text-amber-700',
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}
function monthsSince(date: Date) {
  const now = new Date()
  return Math.max(1, (now.getFullYear() - date.getFullYear()) * 12 + now.getMonth() - date.getMonth())
}
function callDuration(start: Date, end: Date) {
  return Math.round((end.getTime() - start.getTime()) / 60000)
}

const BackIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6" />
  </svg>
)
const PhoneIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.56 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
  </svg>
)

export default async function AdminUserDetailPage({ params }: { params: { id: string } }) {
  const user = await prisma.user.findUnique({
    where: { id: params.id },
    include: {
      subscription: true,
      elders: {
        include: {
          serviceRequests: {
            include: {
              assignment: {
                include: {
                  companion: { include: { user: true } },
                  callSessions: { orderBy: { scheduledAt: 'desc' } },
                  dailyLogs: { orderBy: { createdAt: 'desc' }, take: 3 },
                },
              },
            },
          },
        },
      },
    },
  })

  if (!user) notFound()

  const plan = user.subscription?.plan as string | undefined
  const pricePerMonth = plan ? (PLAN_PRICES[plan] ?? 0) : 0
  const months = user.subscription ? monthsSince(user.subscription.createdAt) : 0
  const totalBilled = pricePerMonth * months

  const allCalls = user.elders.flatMap(e =>
    e.serviceRequests.flatMap(r =>
      (r.assignment?.callSessions ?? []).filter(c => c.status === 'COMPLETED' && c.startedAt && c.endedAt)
    )
  )
  const totalMinutes = allCalls.reduce((sum, c) => sum + (c.startedAt && c.endedAt ? callDuration(c.startedAt, c.endedAt) : 0), 0)

  const avatarPalette = ['bg-primary-100 text-primary-700', 'bg-emerald-100 text-emerald-700', 'bg-violet-100 text-violet-700']
  const avatarColor = avatarPalette[user.name.charCodeAt(0) % avatarPalette.length]

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back */}
      <Link href="/admin/users" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors">
        <BackIcon />Back to users
      </Link>

      {/* User header */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-card p-6">
        <div className="flex items-start gap-5">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center font-bold text-lg flex-shrink-0 ${avatarColor}`}>
            {getInitials(user.name)}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-slate-900">{user.name}</h2>
            <p className="text-slate-500 text-sm">{user.email}</p>
            <p className="text-slate-400 text-xs mt-0.5">Joined {new Date(user.createdAt).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
          </div>
          {user.subscription && (
            <span className={`text-sm px-3 py-1.5 rounded-full font-bold ${PLAN_COLORS[user.subscription.plan]}`}>
              {user.subscription.plan}
            </span>
          )}
        </div>

        {/* Billing summary */}
        <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100">
          {[
            { label: 'Monthly plan', value: `$${pricePerMonth}/mo` },
            { label: 'Months active', value: `${months} mo` },
            { label: 'Total billed', value: `$${totalBilled.toLocaleString()}` },
            { label: 'Total call time', value: `${totalMinutes} min` },
          ].map(s => (
            <div key={s.label}>
              <div className="text-xl font-bold text-slate-900">{s.value}</div>
              <div className="text-xs text-slate-400 mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Elders */}
      {user.elders.map((elder) => {
        const activeReq = elder.serviceRequests.find(r => r.assignment)
        const assignment = activeReq?.assignment
        const companion = assignment?.companion?.user
        const calls = (assignment?.callSessions ?? []).filter(c => c.status === 'COMPLETED' && c.startedAt && c.endedAt)
        const elderMinutes = calls.reduce((sum, c) => sum + callDuration(c.startedAt!, c.endedAt!), 0)
        const recentLogs = assignment?.dailyLogs ?? []
        const elderColor = avatarPalette[elder.name.charCodeAt(0) % avatarPalette.length]
        const companionColor = companion ? avatarPalette[companion.name.charCodeAt(0) % avatarPalette.length] : ''

        return (
          <div key={elder.id} className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
            {/* Elder header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-4">
              <div className={`w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${elderColor}`}>
                {getInitials(elder.name)}
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-slate-900">{elder.name}</h3>
                <p className="text-xs text-slate-500">Age {elder.age} · {elder.timezone} · {elder.language}</p>
              </div>
              {companion && (
                <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${companionColor}`}>
                    {getInitials(companion.name)}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-900">{companion.name}</p>
                    <p className="text-xs text-emerald-600">Companion</p>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Call history */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Call history</p>
                  <span className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full font-semibold">{calls.length} calls · {elderMinutes} min</span>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {calls.slice(0, 8).map((call) => {
                    const dur = callDuration(call.startedAt!, call.endedAt!)
                    return (
                      <div key={call.id} className="flex items-center justify-between text-xs bg-slate-50 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-2 text-slate-600">
                          <span className="text-primary-500"><PhoneIcon /></span>
                          <span>{call.callType}</span>
                          <span className="text-slate-400">{new Date(call.scheduledAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                        </div>
                        <span className="font-semibold text-slate-700">{dur} min</span>
                      </div>
                    )
                  })}
                  {calls.length === 0 && <p className="text-slate-400 text-xs text-center py-4">No completed calls</p>}
                </div>
              </div>

              {/* Recent logs */}
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Recent logs</p>
                <div className="space-y-2">
                  {recentLogs.map((log) => (
                    <div key={log.id} className="bg-slate-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-slate-700">{log.mood}</span>
                        <div className="flex items-center gap-2">
                          {log.medicationTaken !== null && (
                            <span className={`text-xs font-medium ${log.medicationTaken ? 'text-emerald-600' : 'text-red-500'}`}>
                              {log.medicationTaken ? '✓ Med' : '✗ Med'}
                            </span>
                          )}
                          <span className="text-xs text-slate-400">{new Date(log.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-600 line-clamp-2">{log.content}</p>
                      {log.concerns && <p className="text-xs text-amber-600 mt-1 font-medium">{log.concerns}</p>}
                    </div>
                  ))}
                  {recentLogs.length === 0 && <p className="text-slate-400 text-xs text-center py-4">No logs yet</p>}
                </div>
              </div>
            </div>

            {elder.healthNotes && (
              <div className="px-6 pb-5">
                <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
                  <p className="text-xs font-bold text-amber-700 uppercase tracking-wide mb-1">Health notes</p>
                  <p className="text-xs text-slate-700">{elder.healthNotes}</p>
                </div>
              </div>
            )}
          </div>
        )
      })}

      {user.elders.length === 0 && (
        <div className="bg-white border border-slate-100 rounded-xl shadow-card text-center py-10 text-slate-400 text-sm">
          No elders added yet
        </div>
      )}
    </div>
  )
}
