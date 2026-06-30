import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

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
      <h2 className="text-2xl font-bold text-gray-900">Assignments</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Pending Requests ({pendingRequests.length})</h3>
          <div className="space-y-3">
            {pendingRequests.map((req) => (
              <Card key={req.id} className="text-sm">
                <p className="font-medium text-gray-900">{req.elder.name} <span className="text-gray-500">· Age {req.elder.age}</span></p>
                <p className="text-gray-600">Family: {req.elder.family.name}</p>
                <p className="text-gray-600">Timezone: {req.elder.timezone}</p>
                <Badge variant="info" className="mt-2">{req.serviceType}</Badge>
                <div className="mt-3">
                  <label className="block text-xs text-gray-500 mb-1">Assign companion:</label>
                  <form action="/api/assignments" method="POST" className="flex gap-2">
                    <input type="hidden" name="requestId" value={req.id} />
                    <select name="companionId" className="flex-1 text-xs border border-gray-300 rounded-lg px-2 py-1.5">
                      <option value="">Select companion...</option>
                      {approvedCompanions.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.user.name} ({c.languages.join(', ')})
                        </option>
                      ))}
                    </select>
                    <button type="submit" className="px-3 py-1.5 bg-amber-500 text-white text-xs rounded-lg hover:bg-amber-600 font-medium">
                      Assign
                    </button>
                  </form>
                </div>
              </Card>
            ))}
            {pendingRequests.length === 0 && (
              <p className="text-sm text-gray-500 bg-white rounded-xl border p-6 text-center">No pending requests</p>
            )}
          </div>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Available Companions ({approvedCompanions.length})</h3>
          <div className="space-y-3">
            {approvedCompanions.map((c) => (
              <Card key={c.id} className="text-sm">
                <p className="font-medium text-gray-900">{c.user.name}</p>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {c.languages.map((l) => <span key={l} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">{l}</span>)}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
