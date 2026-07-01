import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'

const UsersIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
)
const ClockIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
)
const ClipboardIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
  </svg>
)
const FlagIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" /><line x1="4" y1="22" x2="4" y2="15" />
  </svg>
)

const stats = [
  {
    label: 'Total Families',
    icon: UsersIcon,
    iconBg: 'bg-primary-50',
    iconColor: 'text-primary-700',
    trend: 'active accounts',
  },
  {
    label: 'Pending Verification',
    icon: ClockIcon,
    iconBg: 'bg-amber-50',
    iconColor: 'text-amber-600',
    trend: 'companions awaiting review',
  },
  {
    label: 'Awaiting Assignment',
    icon: ClipboardIcon,
    iconBg: 'bg-violet-50',
    iconColor: 'text-violet-700',
    trend: 'open service requests',
  },
  {
    label: 'Flagged Messages',
    icon: FlagIcon,
    iconBg: 'bg-red-50',
    iconColor: 'text-red-600',
    trend: 'need review',
  },
]

export default async function AdminDashboardPage() {
  const [totalFamilies, pendingCompanions, pendingRequests, flaggedMessages] = await Promise.all([
    prisma.user.count({ where: { role: 'FAMILY' } }),
    prisma.companion.count({ where: { status: 'PENDING' } }),
    prisma.serviceRequest.count({ where: { status: 'PENDING' } }),
    prisma.message.count({ where: { isFlagged: true } }),
  ])

  const values = [totalFamilies, pendingCompanions, pendingRequests, flaggedMessages]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Admin Dashboard</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Platform overview</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label}>
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center mb-4 ${stat.iconBg} ${stat.iconColor}`}>
                <Icon />
              </div>
              <div className="text-3xl font-bold text-slate-900 tabular-nums">{values[i]}</div>
              <div className="text-sm font-semibold text-slate-700 mt-1">{stat.label}</div>
              <div className="text-xs text-slate-400 mt-0.5">{stat.trend}</div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
