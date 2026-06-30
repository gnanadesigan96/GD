import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { scanMessage } from '@/lib/message-scanner'
import { z } from 'zod'

const schema = z.object({
  assignmentId: z.string(),
  receiverId: z.string(),
  content: z.string().min(1).max(2000),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const data = schema.parse(body)
  const scan = scanMessage(data.content)

  const message = await prisma.message.create({
    data: {
      assignmentId: data.assignmentId,
      senderId: (session.user as any).id,
      receiverId: data.receiverId,
      content: data.content,
      isScanned: true,
      isFlagged: scan.isFlagged,
      flagReason: scan.reason,
    },
  })

  if (scan.isFlagged) {
    const companion = await prisma.companion.findFirst({
      where: { userId: (session.user as any).id },
    })

    if (companion) {
      const violationCount = await prisma.privacyViolation.count({
        where: { companionId: companion.id },
      })

      const level = violationCount === 0 ? 'WARNING' : violationCount === 1 ? 'SUSPENSION' : 'BAN'

      await prisma.privacyViolation.create({
        data: { companionId: companion.id, messageId: message.id, level },
      })

      if (level === 'SUSPENSION') {
        await prisma.companion.update({
          where: { id: companion.id },
          data: { status: 'SUSPENDED' },
        })
      } else if (level === 'BAN') {
        await prisma.companion.update({
          where: { id: companion.id },
          data: { status: 'BANNED' },
        })
      }
    }

    return NextResponse.json({ error: 'Message blocked: ' + scan.reason }, { status: 403 })
  }

  return NextResponse.json(message, { status: 201 })
}

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const assignmentId = searchParams.get('assignmentId')
  if (!assignmentId) return NextResponse.json({ error: 'assignmentId required' }, { status: 400 })

  const messages = await prisma.message.findMany({
    where: { assignmentId, isFlagged: false },
    include: { sender: { select: { id: true, name: true, role: true } } },
    orderBy: { createdAt: 'asc' },
  })

  return NextResponse.json(messages)
}
