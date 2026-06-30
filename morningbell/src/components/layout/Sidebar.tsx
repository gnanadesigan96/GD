'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/cn'

interface NavItem {
  label: string
  href: string
  icon: string
}

interface SidebarProps {
  items: NavItem[]
  role: string
}

export function Sidebar({ items, role }: SidebarProps) {
  const pathname = usePathname()
  return (
    <aside className="w-64 min-h-screen bg-white border-r border-amber-100 flex flex-col">
      <div className="p-6 border-b border-amber-100">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔔</span>
          <span className="text-xl font-bold text-amber-600">MorningBell</span>
        </div>
        <p className="text-xs text-gray-500 mt-1 capitalize">{role.toLowerCase()} portal</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              pathname === item.href
                ? 'bg-amber-50 text-amber-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            )}
          >
            <span className="text-lg">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
