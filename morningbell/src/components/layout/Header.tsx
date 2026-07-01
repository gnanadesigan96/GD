'use client'
import { signOut, useSession } from 'next-auth/react'
import { Button } from '@/components/ui/Button'

export function Header({ title }: { title: string }) {
  const { data: session } = useSession()
  return (
    <header className="bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-500">{session?.user?.name}</span>
        <Button variant="ghost" size="sm" onClick={() => signOut({ callbackUrl: '/login' })}>
          Sign out
        </Button>
      </div>
    </header>
  )
}
