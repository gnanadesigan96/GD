import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'
import TeamInviteForm from './TeamInviteForm'

function getInitials(name: string) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}
const avatarPalette = ['bg-primary-100 text-primary-700', 'bg-emerald-100 text-emerald-700', 'bg-violet-100 text-violet-700', 'bg-rose-100 text-rose-700']

export default async function AdminTeamPage() {
  const [team, adminUsers] = await Promise.all([
    prisma.teamMember.findMany({ orderBy: { invitedAt: 'desc' } }),
    prisma.user.findMany({ where: { role: 'ADMIN' }, orderBy: { createdAt: 'asc' } }),
  ])

  const accepted = team.filter(t => t.status === 'ACCEPTED')
  const pending = team.filter(t => t.status === 'PENDING')

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Team</h2>
          <p className="text-slate-500 mt-0.5 text-sm">Manage your internal team members and send invitations</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total members', value: accepted.length + adminUsers.length, color: 'text-slate-900' },
          { label: 'Pending invites', value: pending.length, color: 'text-amber-600' },
          { label: 'Admin accounts', value: adminUsers.length, color: 'text-primary-700' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-slate-100 rounded-xl px-5 py-4 shadow-card">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-slate-500 mt-0.5 font-medium">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Admin accounts */}
      {adminUsers.length > 0 && (
        <div className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-700">Admin accounts</h3>
          </div>
          <div className="divide-y divide-slate-50">
            {adminUsers.map(u => {
              const avatarColor = avatarPalette[u.name.charCodeAt(0) % avatarPalette.length]
              return (
                <div key={u.id} className="flex items-center gap-4 px-6 py-4">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${avatarColor}`}>
                    {getInitials(u.name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900">{u.name}</p>
                    <p className="text-xs text-slate-500">{u.email}</p>
                  </div>
                  <Badge variant="info">Admin</Badge>
                  <span className="text-xs text-slate-400">Since {new Date(u.createdAt).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Team members */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">Team members ({accepted.length + pending.length})</h3>
        </div>
        <div className="divide-y divide-slate-50">
          {team.map(member => {
            const name = member.name || member.email.split('@')[0]
            const avatarColor = avatarPalette[name.charCodeAt(0) % avatarPalette.length]
            const isAccepted = member.status === 'ACCEPTED'
            return (
              <div key={member.id} className="flex items-center gap-4 px-6 py-4">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${isAccepted ? avatarColor : 'bg-slate-100 text-slate-400'}`}>
                  {isAccepted ? getInitials(name) : '?'}
                </div>
                <div className="flex-1 min-w-0">
                  {member.name ? (
                    <>
                      <p className="text-sm font-semibold text-slate-900">{member.name}</p>
                      <p className="text-xs text-slate-500">{member.email}</p>
                    </>
                  ) : (
                    <p className="text-sm text-slate-500 italic">{member.email}</p>
                  )}
                </div>
                <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">{member.role}</span>
                <Badge variant={isAccepted ? 'success' : 'warning'}>
                  {isAccepted ? 'Active' : 'Invited'}
                </Badge>
                <div className="text-right text-xs text-slate-400">
                  {isAccepted && member.acceptedAt
                    ? `Joined ${new Date(member.acceptedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
                    : `Sent ${new Date(member.invitedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
                </div>
                {!isAccepted && (
                  <div className="text-xs text-primary-600 font-medium cursor-pointer hover:text-primary-800">
                    Copy link
                  </div>
                )}
              </div>
            )
          })}
          {team.length === 0 && (
            <div className="text-center py-10 text-slate-400 text-sm">No team members yet. Invite your first one below.</div>
          )}
        </div>
      </div>

      {/* Invite form */}
      <div className="bg-white border border-slate-100 rounded-xl shadow-card p-6">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">Invite a team member</h3>
        <p className="text-xs text-slate-500 mb-5">They'll receive an invitation link to join the MorningBell team.</p>
        <TeamInviteForm />
      </div>
    </div>
  )
}
