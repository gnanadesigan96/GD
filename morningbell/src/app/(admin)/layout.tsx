import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { redirect } from 'next/navigation'

const navItems = [
  { label: 'Dashboard', href: '/admin/dashboard', icon: '📊' },
  { label: 'Companions', href: '/admin/companions', icon: '👤' },
  { label: 'Assignments', href: '/admin/assignments', icon: '🔗' },
  { label: 'Flagged Messages', href: '/admin/flags', icon: '🚩' },
  { label: 'Subscriptions', href: '/admin/subscriptions', icon: '💳' },
]

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions)
  if (!session || (session.user as any).role !== 'ADMIN') redirect('/login')
  return (
    <div className="flex min-h-screen">
      <Sidebar items={navItems} role="Admin" />
      <div className="flex-1 flex flex-col">
        <Header title="Admin Panel" />
        <main className="flex-1 p-6 bg-gray-50">{children}</main>
      </div>
    </div>
  )
}
