import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

const schema = z.object({
  assignmentId: z.string(),
  mood: z.string(),
  medicationTaken: z.boolean().optional(),
  content: z.string().min(1),
  concerns: z.string().optional(),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const companion = await prisma.companion.findFirst({
    where: { userId: (session.user as any).id },
  })
  if (!companion) return NextResponse.json({ error: 'Companion not found' }, { status: 404 })

  const body = await req.json()
  const data = schema.parse(body)

  const log = await prisma.dailyLog.create({
    data: {
      assignmentId: data.assignmentId,
      companionId: companion.id,
      mood: data.mood,
      medicationTaken: data.medicationTaken,
      content: data.content,
      concerns: data.concerns,
    },
  })

  return NextResponse.json(log, { status: 201 })
}

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const assignmentId = searchParams.get('assignmentId')
  if (!assignmentId) return NextResponse.json({ error: 'assignmentId required' }, { status: 400 })

  const logs = await prisma.dailyLog.findMany({
    where: { assignmentId },
    include: { companion: { include: { user: { select: { name: true } } } } },
    orderBy: { createdAt: 'desc' },
  })

  return NextResponse.json(logs)
}
