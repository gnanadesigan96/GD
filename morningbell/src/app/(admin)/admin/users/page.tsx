import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

const PLAN_COLORS: Record<string, string> = {
  COMPANION: 'bg-primary-50 text-primary-700',
  CARETAKER: 'bg-violet-50 text-violet-700',
  PREMIUM: 'bg-amber-50 text-amber-700',
}

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}
const avatarPalette = ['bg-primary-100 text-primary-700', 'bg-emerald-100 text-emerald-700', 'bg-violet-100 text-violet-700', 'bg-rose-100 text-rose-700', 'bg-amber-100 text-amber-700']

const ArrowRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
  </svg>
)

export default async function AdminUsersPage() {
  const users = await prisma.user.findMany({
    where: { role: 'FAMILY' },
    include: {
      subscription: true,
      elders: {
        include: {
          serviceRequests: {
            include: {
              assignment: {
                include: {
                  companion: { include: { user: true } },
                  callSessions: { where: { status: 'COMPLETED' } },
                },
              },
            },
          },
        },
      },
    },
    orderBy: { createdAt: 'desc' },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Family Users</h2>
        <p className="text-slate-500 mt-0.5 text-sm">{users.length} registered families · Click any row to view details</p>
      </div>

      <div className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-12 px-6 py-3 border-b border-slate-100 text-xs font-semibold text-slate-400 uppercase tracking-wide bg-slate-50/60">
          <div className="col-span-4">Family</div>
          <div className="col-span-2">Elders</div>
          <div className="col-span-2">Plan</div>
          <div className="col-span-2">Total calls</div>
          <div className="col-span-1">Joined</div>
          <div className="col-span-1"></div>
        </div>

        <div className="divide-y divide-slate-50">
          {users.map((user) => {
            const totalCalls = user.elders.flatMap(e => e.serviceRequests.flatMap(r => r.assignment?.callSessions ?? [])).length
            const companion = user.elders[0]?.serviceRequests[0]?.assignment?.companion?.user
            const avatarColor = avatarPalette[user.name.charCodeAt(0) % avatarPalette.length]

            return (
              <Link key={user.id} href={`/admin/users/${user.id}`} className="grid grid-cols-12 items-center px-6 py-4 hover:bg-slate-50/70 transition-colors cursor-pointer">
                <div className="col-span-4 flex items-center gap-3 min-w-0">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${avatarColor}`}>
                    {getInitials(user.name)}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{user.name}</p>
                    <p className="text-xs text-slate-500 truncate">{user.email}</p>
                  </div>
                </div>
                <div className="col-span-2 text-sm text-slate-700">
                  {user.elders.length > 0 ? (
                    <span className="font-medium">{user.elders.map(e => e.name).join(', ')}</span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </div>
                <div className="col-span-2">
                  {user.subscription ? (
                    <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${PLAN_COLORS[user.subscription.plan]}`}>
                      {user.subscription.plan}
                    </span>
                  ) : (
                    <Badge variant="warning">No plan</Badge>
                  )}
                </div>
                <div className="col-span-2 text-sm text-slate-700 font-medium">
                  {totalCalls} call{totalCalls !== 1 ? 's' : ''}
                </div>
                <div className="col-span-1 text-xs text-slate-400">
                  {new Date(user.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>
                <div className="col-span-1 flex justify-end text-slate-300 hover:text-primary-500 transition-colors">
                  <ArrowRightIcon />
                </div>
              </Link>
            )
          })}
        </div>

        {users.length === 0 && (
          <div className="text-center py-14 text-slate-400 text-sm">No family users yet</div>
        )}
      </div>
    </div>
  )
}
