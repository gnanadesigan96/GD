import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

export default async function CompanionDashboardPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id

  const companion = await prisma.companion.findFirst({
    where: { userId },
    include: {
      assignments: {
        where: { status: 'ACTIVE' },
        include: {
          request: { include: { elder: true } },
          dailyLogs: { orderBy: { createdAt: 'desc' }, take: 1 },
          callSessions: { where: { status: 'SCHEDULED' }, orderBy: { scheduledAt: 'asc' }, take: 3 },
        },
      },
    },
  })

  if (!companion) return <div className="p-6">Companion profile not found.</div>

  if (companion.status === 'PENDING') {
    return (
      <Card className="text-center py-12">
        <span className="text-5xl">⏳</span>
        <h2 className="text-xl font-semibold text-gray-900 mt-4">Application under review</h2>
        <p className="text-gray-600 mt-2">Your profile and ID are being verified. We'll notify you once approved.</p>
      </Card>
    )
  }

  if (companion.status === 'SUSPENDED') {
    return (
      <Card className="text-center py-12 bg-red-50 border-red-200">
        <span className="text-5xl">⚠️</span>
        <h2 className="text-xl font-semibold text-red-800 mt-4">Account suspended</h2>
        <p className="text-red-700 mt-2">Your account has been suspended due to a privacy policy violation. Contact admin.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Good morning 🌅</h2>
        <p className="text-gray-600 mt-1">You have {companion.assignments.length} active client{companion.assignments.length !== 1 ? 's' : ''}.</p>
      </div>

      {companion.assignments.map((assignment) => {
        const elder = assignment.request.elder
        const lastLog = assignment.dailyLogs[0]
        const nextCall = assignment.callSessions[0]
        return (
          <Card key={assignment.id}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{elder.name}</h3>
                <p className="text-sm text-gray-500">Age {elder.age} · {elder.timezone}</p>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
            {nextCall && (
              <div className="bg-amber-50 rounded-lg p-3 mb-3">
                <p className="text-xs text-amber-700 font-medium">NEXT CALL</p>
                <p className="text-sm text-gray-800 mt-1">
                  {nextCall.callType} · {new Date(nextCall.scheduledAt).toLocaleString()}
                </p>
              </div>
            )}
            {lastLog ? (
              <div className="text-xs text-gray-500">Last log: {new Date(lastLog.createdAt).toLocaleDateString()}</div>
            ) : (
              <Link href="/companion/logs/new" className="text-xs text-amber-600 hover:underline">+ Add today's log</Link>
            )}
          </Card>
        )
      })}

      {companion.assignments.length === 0 && (
        <Card className="text-center py-12">
          <span className="text-5xl">🎉</span>
          <p className="text-gray-600 mt-4">You're approved! Waiting for your first client assignment.</p>
        </Card>
      )}
    </div>
  )
}
