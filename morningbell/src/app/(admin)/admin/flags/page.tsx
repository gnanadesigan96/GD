import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'

const ShieldCheckIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><polyline points="9 12 11 14 15 10" />
  </svg>
)

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
}

export default async function AdminFlagsPage() {
  const violations = await prisma.privacyViolation.findMany({
    include: {
      companion: { include: { user: true } },
      message: { include: { sender: true } },
    },
    orderBy: { createdAt: 'desc' },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Flagged Messages</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Privacy violations and blocked content</p>
      </div>

      {violations.length === 0 ? (
        <div className="bg-white border border-slate-100 rounded-xl shadow-card text-center py-16">
          <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-500">
            <ShieldCheckIcon />
          </div>
          <h3 className="text-base font-semibold text-slate-900">All clear</h3>
          <p className="text-slate-500 text-sm mt-1">No privacy violations reported</p>
        </div>
      ) : (
        <div className="space-y-3">
          {violations.map((v) => {
            const levelColor = v.level === 'BAN' ? 'border-l-red-500' : v.level === 'SUSPENSION' ? 'border-l-amber-500' : 'border-l-primary-400'
            return (
              <div key={v.id} className={`bg-white border border-slate-100 border-l-4 ${levelColor} rounded-xl shadow-card p-5`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-9 h-9 rounded-full bg-red-50 text-red-500 flex items-center justify-center font-bold text-xs flex-shrink-0">
                      {getInitials(v.companion.user.name || '??')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <p className="font-semibold text-slate-900 text-sm">{v.companion.user.name}</p>
                        <Badge variant={v.level === 'BAN' ? 'danger' : v.level === 'SUSPENSION' ? 'warning' : 'info'}>
                          {v.level}
                        </Badge>
                      </div>
                      <div className="bg-red-50 border border-red-100 rounded-lg p-3 mb-2">
                        <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1">Blocked message</p>
                        <p className="text-sm text-slate-700 leading-relaxed">{v.message.content}</p>
                        {v.message.flagReason && (
                          <p className="text-xs text-slate-500 mt-1.5">Reason: <span className="font-medium text-slate-600">{v.message.flagReason}</span></p>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{new Date(v.createdAt).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}</p>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
