import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/companion/dashboard', icon: '🏠' },
  { label: 'Messages', href: '/companion/messages', icon: '💬' },
  { label: 'Calls', href: '/companion/calls', icon: '📞' },
  { label: 'Daily Logs', href: '/companion/logs/new', icon: '📝' },
  { label: 'My Profile', href: '/companion/profile', icon: '👤' },
]

export default async function CompanionLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  if (!session || (session.user as any).role !== 'COMPANION') redirect('/login')
  return (
    <div className="flex min-h-screen">
      <Sidebar items={navItems} role="Companion" />
      <div className="flex-1 flex flex-col">
        <Header title="MorningBell" />
        <main className="flex-1 p-6 bg-amber-50/30">{children}</main>
      </div>
    </div>
  )
}
