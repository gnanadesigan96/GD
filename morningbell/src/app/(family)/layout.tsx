import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'My Elder', href: '/onboarding', icon: 'elder' },
  { label: 'Messages', href: '/messages', icon: 'messages' },
  { label: 'Calls', href: '/calls', icon: 'calls' },
  { label: 'Daily Logs', href: '/logs', icon: 'logs' },
  { label: 'Subscription', href: '/subscription', icon: 'subscriptions' },
]

export default async function FamilyLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  if (!session) redirect('/login')
  if ((session.user as any).role === 'ADMIN') redirect('/admin/dashboard')
  if ((session.user as any).role === 'COMPANION') redirect('/companion/dashboard')

  return (
    <div className="flex min-h-screen">
      <Sidebar items={navItems} role="Family" />
      <div className="flex-1 flex flex-col">
        <Header title="MorningBell" />
        <main className="flex-1 p-6 bg-slate-50">{children}</main>
      </div>
    </div>
  )
}
