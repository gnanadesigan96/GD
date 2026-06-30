import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { generateChannelName } from '@/lib/agora'
import { z } from 'zod'

const schema = z.object({
  assignmentId: z.string(),
  callType: z.enum(['VIDEO', 'VOICE']),
  scheduledAt: z.string(),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const data = schema.parse(body)
  const channelName = generateChannelName(data.assignmentId)

  const call = await prisma.callSession.create({
    data: {
      assignmentId: data.assignmentId,
      agoraChannelName: channelName,
      callType: data.callType,
      scheduledAt: new Date(data.scheduledAt),
    },
  })

  return NextResponse.json(call, { status: 201 })
}

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const assignmentId = searchParams.get('assignmentId')
  if (!assignmentId) return NextResponse.json({ error: 'assignmentId required' }, { status: 400 })

  const calls = await prisma.callSession.findMany({
    where: { assignmentId },
    orderBy: { scheduledAt: 'asc' },
  })

  return NextResponse.json(calls)
}
