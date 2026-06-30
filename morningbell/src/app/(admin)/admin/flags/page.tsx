import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

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
      <h2 className="text-2xl font-bold text-gray-900">Flagged Messages & Violations</h2>
      <div className="space-y-4">
        {violations.map((v) => (
          <Card key={v.id}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <p className="font-semibold text-gray-900">{v.companion.user.name}</p>
                  <Badge variant={v.level === 'BAN' ? 'danger' : v.level === 'SUSPENSION' ? 'warning' : 'info'}>
                    {v.level}
                  </Badge>
                </div>
                <div className="bg-red-50 rounded-lg p-3 mb-2">
                  <p className="text-xs text-red-600 font-medium mb-1">BLOCKED MESSAGE</p>
                  <p className="text-sm text-gray-700">{v.message.content}</p>
                  <p className="text-xs text-gray-500 mt-1">Reason: {v.message.flagReason}</p>
                </div>
                <p className="text-xs text-gray-500">
                  {new Date(v.createdAt).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
        ))}
        {violations.length === 0 && (
          <div className="text-center py-12 bg-white rounded-xl border">
            <span className="text-4xl">✅</span>
            <p className="text-gray-600 mt-3">No privacy violations reported</p>
          </div>
        )}
      </div>
    </div>
  )
}
