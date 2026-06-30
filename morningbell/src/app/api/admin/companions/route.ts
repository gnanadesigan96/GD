import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

const schema = z.object({
  companionId: z.string(),
  action: z.enum(['approve', 'suspend', 'ban']),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session || (session.user as any).role !== 'ADMIN') {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const body = await req.json()
  const data = schema.parse(body)

  const statusMap = { approve: 'APPROVED', suspend: 'SUSPENDED', ban: 'BANNED' } as const

  const companion = await prisma.companion.update({
    where: { id: data.companionId },
    data: { status: statusMap[data.action] },
  })

  return NextResponse.json(companion)
}
