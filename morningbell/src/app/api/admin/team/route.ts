import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session || (session.user as any).role !== 'ADMIN') {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  const { email, role } = await req.json()
  if (!email) return NextResponse.json({ error: 'Email required' }, { status: 400 })

  try {
    const member = await prisma.teamMember.create({
      data: { email, role: role || 'Support', status: 'PENDING' },
    })
    return NextResponse.json(member)
  } catch {
    return NextResponse.json({ error: 'Email already invited' }, { status: 409 })
  }
}
