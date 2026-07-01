import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

const ClockIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
)
const ShieldIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
)
const SparkleIcon = () => (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
)
const CalendarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
  </svg>
)
const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
}

export default async function CompanionDashboardPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id
  const userName = (session!.user as any).name || 'there'

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

  if (!companion) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="text-center py-14 max-w-sm mx-auto">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4 text-red-400">
            <ShieldIcon />
          </div>
          <h2 className="text-base font-semibold text-slate-900">Profile not found</h2>
          <p className="text-slate-500 text-sm mt-1">Contact support if this is unexpected.</p>
        </Card>
      </div>
    )
  }

  if (companion.status === 'PENDING') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="text-center py-14 max-w-sm mx-auto">
          <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-4 text-amber-500">
            <ClockIcon />
          </div>
          <h2 className="text-base font-semibold text-slate-900 mt-2">Application under review</h2>
          <p className="text-slate-500 text-sm mt-2 max-w-xs mx-auto">Your profile and ID are being verified. We'll notify you once approved — usually within 1–2 business days.</p>
        </Card>
      </div>
    )
  }

  if (companion.status === 'SUSPENDED') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="text-center py-14 max-w-sm mx-auto border-red-100">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4 text-red-400">
            <ShieldIcon />
          </div>
          <h2 className="text-base font-semibold text-red-800 mt-2">Account suspended</h2>
          <p className="text-red-600 text-sm mt-2 max-w-xs mx-auto">Your account has been suspended due to a policy violation. Please contact the admin team for details.</p>
        </Card>
      </div>
    )
  }

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Good morning, {userName.split(' ')[0]}</h1>
          <p className="text-slate-500 mt-0.5 text-sm">{today}</p>
        </div>
        <Link
          href="/companion/logs/new"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-all duration-150 cursor-pointer shadow-sm"
        >
          <PlusIcon />
          New log
        </Link>
      </div>

      {/* No assignments */}
      {companion.assignments.length === 0 && (
        <Card className="text-center py-14">
          <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4 text-primary-500">
            <SparkleIcon />
          </div>
          <h3 className="text-base font-semibold text-slate-900">You're approved!</h3>
          <p className="text-slate-500 text-sm mt-1 max-w-xs mx-auto">Waiting for your first client assignment. We'll notify you when one is ready.</p>
        </Card>
      )}

      {/* Assignment cards */}
      {companion.assignments.map((assignment) => {
        const elder = assignment.request.elder
        const lastLog = assignment.dailyLogs[0]
        const nextCall = assignment.callSessions[0]
        const initials = getInitials(elder.name)
        const colors = ['bg-primary-100 text-primary-700', 'bg-emerald-100 text-emerald-700', 'bg-violet-100 text-violet-700']
        const avatarColor = colors[elder.name.charCodeAt(0) % colors.length]

        return (
          <Card key={assignment.id}>
            {/* Elder header */}
            <div className="flex items-center gap-4 mb-5">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${avatarColor}`}>
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900">{elder.name}</h3>
                <p className="text-sm text-slate-500">Age {elder.age} · {elder.timezone}</p>
              </div>
              <Badge variant="success">Active</Badge>
            </div>

            {/* Next call */}
            {nextCall && (
              <div className="flex items-start gap-3 bg-primary-50 border border-primary-100 rounded-xl px-4 py-3 mb-4">
                <div className="text-primary-500 mt-0.5">
                  <CalendarIcon />
                </div>
                <div>
                  <p className="text-xs font-semibold text-primary-700 uppercase tracking-wide">Next call</p>
                  <p className="text-sm text-slate-700 mt-0.5 font-medium">
                    {nextCall.callType} · {new Date(nextCall.scheduledAt).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            )}

            {/* Log status */}
            {lastLog ? (
              <div className="flex items-center justify-between text-sm text-slate-500 border border-slate-100 rounded-xl px-4 py-3 bg-slate-50">
                <span>Last log submitted</span>
                <span className="font-medium text-slate-700">{new Date(lastLog.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            ) : (
              <Link
                href="/companion/logs/new"
                className="flex items-center justify-center gap-2 w-full border-2 border-dashed border-primary-200 text-primary-600 hover:border-primary-400 hover:bg-primary-50 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-150 cursor-pointer"
              >
                <PlusIcon />
                Add today's log
              </Link>
            )}
          </Card>
        )
      })}
    </div>
  )
}
