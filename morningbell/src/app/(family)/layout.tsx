import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: '🏠' },
  { label: 'My Elder', href: '/onboarding', icon: '👴' },
  { label: 'Messages', href: '/messages', icon: '💬' },
  { label: 'Calls', href: '/calls', icon: '📞' },
  { label: 'Daily Logs', href: '/logs', icon: '📋' },
  { label: 'Subscription', href: '/subscription', icon: '💳' },
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
        <main className="flex-1 p-6 bg-amber-50/30">{children}</main>
      </div>
    </div>
  )
}
