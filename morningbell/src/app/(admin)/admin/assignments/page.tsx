import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'

const selectClass = 'flex-1 text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
}

export default async function AdminAssignmentsPage() {
  const pendingRequests = await prisma.serviceRequest.findMany({
    where: { status: 'PENDING' },
    include: { elder: { include: { family: true } } },
    orderBy: { createdAt: 'asc' },
  })
  const approvedCompanions = await prisma.companion.findMany({
    where: { status: 'APPROVED' },
    include: { user: true },
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Assignments</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Match pending requests with available companions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending requests */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700">Pending Requests</h3>
            <span className="text-xs bg-amber-50 text-amber-700 px-2.5 py-0.5 rounded-full font-semibold">{pendingRequests.length}</span>
          </div>
          <div className="space-y-3">
            {pendingRequests.map((req) => (
              <div key={req.id} className="bg-white border border-slate-100 rounded-xl shadow-card p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold text-slate-900 text-sm">{req.elder.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">Age {req.elder.age} · {req.elder.timezone}</p>
                    <p className="text-xs text-slate-500">Family: {req.elder.family.name}</p>
                  </div>
                  <Badge variant="warning">{req.serviceType.replace(/_/g, ' ')}</Badge>
                </div>
                <div>
                  <label className="block text-xs text-slate-500 font-medium mb-1.5">Assign companion</label>
                  <form action="/api/assignments" method="POST" className="flex gap-2">
                    <input type="hidden" name="requestId" value={req.id} />
                    <select name="companionId" className={selectClass}>
                      <option value="">Select companion...</option>
                      {approvedCompanions.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.user.name} ({c.languages.join(', ')})
                        </option>
                      ))}
                    </select>
                    <button type="submit"
                      className="px-4 py-2 bg-primary-700 text-white text-xs font-semibold rounded-lg hover:bg-primary-800 transition-colors cursor-pointer flex-shrink-0">
                      Assign
                    </button>
                  </form>
                </div>
              </div>
            ))}
            {pendingRequests.length === 0 && (
              <div className="bg-white border border-slate-100 rounded-xl p-8 text-center text-slate-400 text-sm shadow-card">
                All requests have been assigned
              </div>
            )}
          </div>
        </div>

        {/* Available companions */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700">Available Companions</h3>
            <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full font-semibold">{approvedCompanions.length}</span>
          </div>
          <div className="space-y-2">
            {approvedCompanions.map((c) => (
              <div key={c.id} className="bg-white border border-slate-100 rounded-xl shadow-card px-5 py-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                  {getInitials(c.user.name || '??')}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900">{c.user.name}</p>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {c.languages.map((l) => (
                      <span key={l} className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full font-medium">{l}</span>
                    ))}
                  </div>
                </div>
                <Badge variant="success">Ready</Badge>
              </div>
            ))}
            {approvedCompanions.length === 0 && (
              <div className="bg-white border border-slate-100 rounded-xl p-8 text-center text-slate-400 text-sm shadow-card">
                No approved companions yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
