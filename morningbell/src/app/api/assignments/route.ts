import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

const schema = z.object({
  requestId: z.string(),
  companionId: z.string(),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user || (session.user as any).role !== 'ADMIN') {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const body = await req.json()
  const data = schema.parse(body)

  const assignment = await prisma.assignment.create({
    data: {
      requestId: data.requestId,
      companionId: data.companionId,
    },
  })

  await prisma.serviceRequest.update({
    where: { id: data.requestId },
    data: { status: 'ASSIGNED' },
  })

  return NextResponse.json(assignment, { status: 201 })
}
