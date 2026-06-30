import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

export default async function AdminCompanionsPage() {
  const companions = await prisma.companion.findMany({
    include: { user: true },
    orderBy: { createdAt: 'desc' },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Companions</h2>
      <div className="space-y-4">
        {companions.map((companion) => (
          <Card key={companion.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900">{companion.user.name}</p>
                <p className="text-sm text-gray-500">{companion.user.email}</p>
                <div className="flex gap-2 mt-2 flex-wrap">
                  {companion.languages.map((lang) => (
                    <span key={lang} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">{lang}</span>
                  ))}
                  {companion.skills.slice(0, 3).map((skill) => (
                    <span key={skill} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{skill}</span>
                  ))}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge variant={
                  companion.status === 'APPROVED' ? 'success' :
                  companion.status === 'PENDING' ? 'warning' :
                  companion.status === 'SUSPENDED' ? 'danger' : 'danger'
                }>
                  {companion.status}
                </Badge>
                <Badge variant={companion.idVerified ? 'success' : 'warning'}>
                  {companion.idVerified ? 'ID Verified' : 'ID Pending'}
                </Badge>
                {companion.status === 'PENDING' && (
                  <form action={`/api/admin/companions`} method="POST">
                    <input type="hidden" name="companionId" value={companion.id} />
                    <input type="hidden" name="action" value="approve" />
                    <button
                      type="submit"
                      className="px-3 py-1.5 text-xs font-medium bg-green-500 text-white rounded-lg hover:bg-green-600"
                    >
                      Approve
                    </button>
                  </form>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
