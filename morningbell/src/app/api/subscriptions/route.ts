import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { stripe, PLANS } from '@/lib/stripe'
import { prisma } from '@/lib/prisma'

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session?.user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json().catch(() => null) || await req.formData().then(f => ({ plan: f.get('plan') })).catch(() => ({ plan: 'COMPANION' }))
  const plan = body.plan as keyof typeof PLANS
  const planDetails = PLANS[plan]
  if (!planDetails) return NextResponse.json({ error: 'Invalid plan' }, { status: 400 })

  const userId = (session.user as any).id
  const user = await prisma.user.findUnique({ where: { id: userId } })
  if (!user) return NextResponse.json({ error: 'User not found' }, { status: 404 })

  let sub = await prisma.subscription.findUnique({ where: { userId } })
  let customerId = sub?.stripeCustomerId

  if (!customerId) {
    const customer = await stripe.customers.create({ email: user.email, name: user.name })
    customerId = customer.id
  }

  const checkoutSession = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: 'subscription',
    payment_method_types: ['card'],
    line_items: [{ price: planDetails.priceId, quantity: 1 }],
    success_url: `${process.env.NEXTAUTH_URL}/dashboard?subscribed=1`,
    cancel_url: `${process.env.NEXTAUTH_URL}/subscription`,
    metadata: { userId, plan },
  })

  return NextResponse.redirect(checkoutSession.url!)
}
