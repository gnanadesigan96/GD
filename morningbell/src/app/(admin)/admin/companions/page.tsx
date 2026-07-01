import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
}
const avatarColors = ['bg-primary-100 text-primary-700', 'bg-emerald-100 text-emerald-700', 'bg-violet-100 text-violet-700', 'bg-rose-100 text-rose-700', 'bg-amber-100 text-amber-700']

export default async function AdminCompanionsPage() {
  const companions = await prisma.companion.findMany({
    include: { user: true },
    orderBy: { createdAt: 'desc' },
  })

  const counts = {
    total: companions.length,
    approved: companions.filter(c => c.status === 'APPROVED').length,
    pending: companions.filter(c => c.status === 'PENDING').length,
    suspended: companions.filter(c => c.status === 'SUSPENDED').length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Companions</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Manage companion applications and status</p>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total', value: counts.total, color: 'text-slate-900' },
          { label: 'Approved', value: counts.approved, color: 'text-emerald-700' },
          { label: 'Pending', value: counts.pending, color: 'text-amber-600' },
          { label: 'Suspended', value: counts.suspended, color: 'text-red-600' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-slate-100 rounded-xl px-5 py-4 shadow-card">
            <div className={`text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</div>
            <div className="text-xs text-slate-500 mt-0.5 font-medium">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">All companions ({counts.total})</h3>
        </div>
        <div className="divide-y divide-slate-50">
          {companions.map((companion) => {
            const avatarColor = avatarColors[companion.user.name?.charCodeAt(0) ?? 0 % avatarColors.length]
            return (
              <div key={companion.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/60 transition-colors">
                {/* Avatar */}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${avatarColor}`}>
                  {getInitials(companion.user.name || '??')}
                </div>

                {/* Name + email */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900">{companion.user.name}</p>
                  <p className="text-xs text-slate-500">{companion.user.email}</p>
                </div>

                {/* Languages */}
                <div className="hidden lg:flex items-center gap-1.5 flex-wrap max-w-[200px]">
                  {companion.languages.slice(0, 3).map((lang) => (
                    <span key={lang} className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full font-medium">{lang}</span>
                  ))}
                  {companion.skills.slice(0, 2).map((skill) => (
                    <span key={skill} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">{skill}</span>
                  ))}
                </div>

                {/* Badges */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Badge variant={companion.idVerified ? 'success' : 'warning'}>
                    {companion.idVerified ? 'ID Verified' : 'ID Pending'}
                  </Badge>
                  <Badge variant={
                    companion.status === 'APPROVED' ? 'success' :
                    companion.status === 'PENDING' ? 'warning' : 'danger'
                  }>
                    {companion.status.charAt(0) + companion.status.slice(1).toLowerCase()}
                  </Badge>
                </div>

                {/* Action */}
                {companion.status === 'PENDING' && (
                  <form action="/api/admin/companions" method="POST" className="flex-shrink-0">
                    <input type="hidden" name="companionId" value={companion.id} />
                    <input type="hidden" name="action" value="approve" />
                    <button
                      type="submit"
                      className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors cursor-pointer"
                    >
                      Approve
                    </button>
                  </form>
                )}
              </div>
            )
          })}
        </div>
        {companions.length === 0 && (
          <div className="text-center py-14 text-slate-400 text-sm">No companions registered yet</div>
        )}
      </div>
    </div>
  )
}
