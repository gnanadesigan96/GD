import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

export default async function FamilyDashboardPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id

  const elders = await prisma.elder.findMany({
    where: { familyId: userId },
    include: {
      serviceRequests: {
        include: {
          assignment: {
            include: {
              companion: { include: { user: true } },
              dailyLogs: { orderBy: { createdAt: 'desc' }, take: 1 },
            },
          },
        },
      },
    },
  })

  const subscription = await prisma.subscription.findUnique({ where: { userId } })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Welcome back 👋</h2>
        <p className="text-gray-600 mt-1">Here's how your loved ones are doing today.</p>
      </div>

      {!subscription && (
        <Card className="bg-amber-50 border-amber-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-amber-800">No active subscription</p>
              <p className="text-sm text-amber-700 mt-1">Choose a plan to get a companion assigned.</p>
            </div>
            <Link href="/subscription" className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600">
              View plans
            </Link>
          </div>
        </Card>
      )}

      {elders.length === 0 && (
        <Card>
          <div className="text-center py-8">
            <span className="text-5xl">👴</span>
            <p className="text-gray-600 mt-4">You haven't added a loved one yet.</p>
            <Link href="/onboarding" className="inline-block mt-4 px-6 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600">
              Add your loved one
            </Link>
          </div>
        </Card>
      )}

      {elders.map((elder) => {
        const activeRequest = elder.serviceRequests.find((r) => r.status === 'ACTIVE' || r.status === 'ASSIGNED')
        const assignment = activeRequest?.assignment
        const lastLog = assignment?.dailyLogs[0]

        return (
          <Card key={elder.id}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{elder.name}</h3>
                <p className="text-sm text-gray-500">Age {elder.age} · {elder.timezone}</p>
              </div>
              <Badge variant={assignment ? 'success' : 'warning'}>
                {assignment ? 'Companion assigned' : 'Awaiting assignment'}
              </Badge>
            </div>

            {assignment && (
              <div className="bg-green-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-gray-700">
                  <span className="font-medium">Companion:</span> {assignment.companion.user.name}
                </p>
              </div>
            )}

            {lastLog && (
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-xs text-blue-600 font-medium mb-1">LATEST LOG</p>
                <p className="text-sm text-gray-700">{lastLog.content}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Mood: {lastLog.mood} · {lastLog.medicationTaken !== null ? (lastLog.medicationTaken ? '✓ Medication taken' : '✗ Medication not taken') : ''}
                </p>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
