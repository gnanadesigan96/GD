import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function GET() {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const companion = await prisma.companion.findFirst({
    where: { userId: (session.user as any).id },
  })

  if (!companion) return NextResponse.json([])

  const assignments = await prisma.assignment.findMany({
    where: { companionId: companion.id, status: 'ACTIVE' },
    include: { request: { include: { elder: true } } },
  })

  return NextResponse.json(assignments)
}
