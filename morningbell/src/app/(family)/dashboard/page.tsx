import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import Link from 'next/link'

const UserCircleIcon = () => (
  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
  </svg>
)
const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
)
const ArrowRightIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
  </svg>
)
const CreditCardIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
  </svg>
)

function getInitials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
}

function getAvatarColor(name: string) {
  const colors = [
    'bg-primary-100 text-primary-700',
    'bg-emerald-100 text-emerald-700',
    'bg-violet-100 text-violet-700',
    'bg-rose-100 text-rose-700',
    'bg-amber-100 text-amber-700',
  ]
  const idx = name.charCodeAt(0) % colors.length
  return colors[idx]
}

export default async function FamilyDashboardPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id
  const userName = (session!.user as any).name || 'there'

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

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Good morning, {userName.split(' ')[0]}</h1>
          <p className="text-slate-500 mt-0.5 text-sm">{today}</p>
        </div>
        {elders.length > 0 && (
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all duration-150 cursor-pointer shadow-card"
          >
            <PlusIcon />
            Add loved one
          </Link>
        )}
      </div>

      {/* Subscription banner */}
      {!subscription && (
        <div className="rounded-xl bg-gradient-to-r from-primary-700 to-primary-600 p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-white flex-shrink-0">
                <CreditCardIcon />
              </div>
              <div>
                <p className="font-semibold text-white">No active subscription</p>
                <p className="text-primary-200 text-sm mt-0.5">Choose a plan to get a companion assigned to your loved one.</p>
              </div>
            </div>
            <Link
              href="/subscription"
              className="flex-shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-white text-primary-700 rounded-lg text-sm font-semibold hover:bg-primary-50 transition-all duration-150 cursor-pointer shadow-sm"
            >
              View plans
              <ArrowRightIcon />
            </Link>
          </div>
        </div>
      )}

      {/* Empty state */}
      {elders.length === 0 && (
        <Card>
          <div className="text-center py-14">
            <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-5 text-slate-300">
              <UserCircleIcon />
            </div>
            <h3 className="text-base font-semibold text-slate-900 mb-1">No loved ones added yet</h3>
            <p className="text-sm text-slate-500 mb-6 max-w-xs mx-auto">Add your elderly parent or loved one to get them matched with a care companion.</p>
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary-700 text-white rounded-lg text-sm font-semibold hover:bg-primary-800 transition-all duration-150 cursor-pointer shadow-sm"
            >
              <PlusIcon />
              Add your loved one
            </Link>
          </div>
        </Card>
      )}

      {/* Elder cards */}
      {elders.map((elder) => {
        const activeRequest = elder.serviceRequests.find((r) => r.status === 'ACTIVE' || r.status === 'ASSIGNED')
        const assignment = activeRequest?.assignment
        const lastLog = assignment?.dailyLogs[0]
        const companionName = assignment?.companion.user.name || ''

        return (
          <Card key={elder.id}>
            {/* Elder header */}
            <div className="flex items-center gap-4 mb-5">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${getAvatarColor(elder.name)}`}>
                {getInitials(elder.name)}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-slate-900">{elder.name}</h3>
                <p className="text-sm text-slate-500">Age {elder.age} · {elder.timezone}</p>
              </div>
              <Badge variant={assignment ? 'success' : 'warning'}>
                {assignment ? 'Companion assigned' : 'Awaiting assignment'}
              </Badge>
            </div>

            {/* Companion info */}
            {assignment && companionName && (
              <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3 mb-4">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-xs flex-shrink-0 ${getAvatarColor(companionName)}`}>
                  {getInitials(companionName)}
                </div>
                <div>
                  <p className="text-xs text-emerald-600 font-medium">Your companion</p>
                  <p className="text-sm font-semibold text-slate-900">{companionName}</p>
                </div>
              </div>
            )}

            {/* Latest log */}
            {lastLog && (
              <div className="border border-slate-100 rounded-xl p-4 bg-slate-50">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Latest log</p>
                <p className="text-sm text-slate-700 leading-relaxed">{lastLog.content}</p>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
                  {lastLog.mood && <span>Mood: <span className="font-medium text-slate-700">{lastLog.mood}</span></span>}
                  {lastLog.medicationTaken !== null && (
                    <span className={lastLog.medicationTaken ? 'text-emerald-600 font-medium' : 'text-red-500 font-medium'}>
                      {lastLog.medicationTaken ? '✓ Medication taken' : '✗ Medication missed'}
                    </span>
                  )}
                </div>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
