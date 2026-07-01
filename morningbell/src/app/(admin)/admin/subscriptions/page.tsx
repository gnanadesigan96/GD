import { prisma } from '@/lib/prisma'
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

const TrendUpIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
  </svg>
)
const UsersIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
)
const DollarIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </svg>
)

export default async function AdminSubscriptionsPage() {
  const subscriptions = await prisma.subscription.findMany({
    include: { user: { include: { elders: true } } },
    orderBy: { createdAt: 'desc' },
  })

  const mrr = subscriptions.reduce((sum, s) => sum + (PLAN_PRICES[s.plan] ?? 0), 0)
  const totalRevenue = subscriptions.reduce((sum, s) => sum + (PLAN_PRICES[s.plan] ?? 0) * monthsSince(s.createdAt), 0)
  const byPlan = { COMPANION: 0, CARETAKER: 0, PREMIUM: 0 }
  subscriptions.forEach(s => { if (s.plan in byPlan) byPlan[s.plan as keyof typeof byPlan]++ })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Subscriptions</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Revenue overview and all active family plans</p>
      </div>

      {/* Revenue cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-card">
          <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center mb-3">
            <DollarIcon />
          </div>
          <div className="text-2xl font-bold text-slate-900">${mrr.toLocaleString()}</div>
          <div className="text-xs text-slate-500 mt-0.5 font-medium">Monthly Recurring Revenue</div>
          <div className="flex items-center gap-1 text-xs text-emerald-600 font-medium mt-2">
            <TrendUpIcon /><span>Active</span>
          </div>
        </div>
        <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-card">
          <div className="w-10 h-10 bg-primary-50 text-primary-700 rounded-xl flex items-center justify-center mb-3">
            <UsersIcon />
          </div>
          <div className="text-2xl font-bold text-slate-900">{subscriptions.length}</div>
          <div className="text-xs text-slate-500 mt-0.5 font-medium">Total Subscribers</div>
        </div>
        <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-card">
          <div className="w-10 h-10 bg-amber-50 text-amber-600 rounded-xl flex items-center justify-center mb-3">
            <DollarIcon />
          </div>
          <div className="text-2xl font-bold text-slate-900">${totalRevenue.toLocaleString()}</div>
          <div className="text-xs text-slate-500 mt-0.5 font-medium">Total Revenue (all-time)</div>
        </div>
        <div className="bg-white border border-slate-100 rounded-xl p-5 shadow-card">
          <div className="text-2xl font-bold text-slate-900">${subscriptions.length > 0 ? Math.round(mrr / subscriptions.length) : 0}</div>
          <div className="text-xs text-slate-500 mt-0.5 font-medium">Avg Revenue per User</div>
          <div className="flex gap-2 mt-3">
            {Object.entries(byPlan).map(([plan, count]) => (
              <span key={plan} className={`text-xs px-2 py-0.5 rounded-full font-medium ${PLAN_COLORS[plan]}`}>{plan.charAt(0)}: {count}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Subscriptions table */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">All subscriptions ({subscriptions.length})</h3>
        </div>
        <div className="divide-y divide-slate-50">
          {subscriptions.map((sub) => {
            const price = PLAN_PRICES[sub.plan] ?? 0
            const months = monthsSince(sub.createdAt)
            const totalBilled = price * months
            const avatarColors = ['bg-primary-100 text-primary-700', 'bg-violet-100 text-violet-700', 'bg-emerald-100 text-emerald-700', 'bg-rose-100 text-rose-700']
            const avatarColor = avatarColors[sub.user.name.charCodeAt(0) % avatarColors.length]
            return (
              <div key={sub.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/60 transition-colors">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${avatarColor}`}>
                  {getInitials(sub.user.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <Link href={`/admin/users/${sub.userId}`} className="text-sm font-semibold text-slate-900 hover:text-primary-700 transition-colors">
                    {sub.user.name}
                  </Link>
                  <p className="text-xs text-slate-500">{sub.user.email}</p>
                </div>
                <div className="hidden sm:block text-xs text-slate-500">{sub.user.elders.length} elder{sub.user.elders.length !== 1 ? 's' : ''}</div>
                <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${PLAN_COLORS[sub.plan]}`}>{sub.plan}</span>
                <div className="text-right hidden md:block">
                  <div className="text-sm font-bold text-slate-900">${price}/mo</div>
                  <div className="text-xs text-slate-400">total ${totalBilled.toLocaleString()}</div>
                </div>
                <Badge variant={sub.status === 'active' ? 'success' : 'warning'}>
                  {sub.status}
                </Badge>
                <div className="text-xs text-slate-400 hidden lg:block">
                  {sub.currentPeriodEnd ? `Renews ${new Date(sub.currentPeriodEnd).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : '—'}
                </div>
              </div>
            )
          })}
        </div>
        {subscriptions.length === 0 && (
          <div className="text-center py-14 text-slate-400 text-sm">No subscriptions yet</div>
        )}
      </div>
    </div>
  )
}
