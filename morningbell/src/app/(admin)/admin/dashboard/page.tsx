import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'

export default async function AdminDashboardPage() {
  const [totalFamilies, pendingCompanions, pendingRequests, flaggedMessages] = await Promise.all([
    prisma.user.count({ where: { role: 'FAMILY' } }),
    prisma.companion.count({ where: { status: 'PENDING' } }),
    prisma.serviceRequest.count({ where: { status: 'PENDING' } }),
    prisma.message.count({ where: { isFlagged: true } }),
  ])

  const stats = [
    { label: 'Total Families', value: totalFamilies, icon: '👨‍👩‍👧', color: 'bg-blue-50 text-blue-700' },
    { label: 'Companions Pending Verification', value: pendingCompanions, icon: '⏳', color: 'bg-amber-50 text-amber-700' },
    { label: 'Requests Awaiting Assignment', value: pendingRequests, icon: '📋', color: 'bg-purple-50 text-purple-700' },
    { label: 'Flagged Messages', value: flaggedMessages, icon: '🚩', color: 'bg-red-50 text-red-700' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Admin Dashboard</h2>
        <p className="text-gray-600 mt-1">Platform overview</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} className={stat.color}>
            <div className="text-3xl mb-2">{stat.icon}</div>
            <div className="text-3xl font-bold">{stat.value}</div>
            <div className="text-sm font-medium mt-1">{stat.label}</div>
          </Card>
        ))}
      </div>
    </div>
  )
}
