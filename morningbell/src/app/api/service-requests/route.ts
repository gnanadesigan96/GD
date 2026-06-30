import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

const schema = z.object({
  elderId: z.string(),
  serviceType: z.enum(['COMPANION', 'CARETAKER', 'ACTIVITY_COACH', 'COORDINATOR']),
  parameters: z.record(z.any()),
})

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const data = schema.parse(body)

  const request = await prisma.serviceRequest.create({
    data: {
      elderId: data.elderId,
      serviceType: data.serviceType,
      parameters: data.parameters,
    },
  })

  return NextResponse.json(request, { status: 201 })
}
