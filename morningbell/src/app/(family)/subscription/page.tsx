import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { PLANS } from '@/lib/stripe'
import { prisma } from '@/lib/prisma'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

export default async function SubscriptionPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id
  const subscription = await prisma.subscription.findUnique({ where: { userId } })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Subscription</h2>

      {subscription && (
        <Card className="bg-green-50 border-green-200">
          <p className="font-semibold text-green-800">Active: {subscription.plan} plan</p>
          {subscription.currentPeriodEnd && (
            <p className="text-sm text-green-700 mt-1">Renews {new Date(subscription.currentPeriodEnd).toLocaleDateString()}</p>
          )}
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(PLANS).map(([key, plan]) => (
          <Card key={key} className={subscription?.plan === key ? 'border-amber-400 bg-amber-50' : ''}>
            {subscription?.plan === key && <Badge variant="success" className="mb-3">Current plan</Badge>}
            <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
            <div className="text-3xl font-bold text-gray-900 my-3">${plan.price}<span className="text-base font-normal text-gray-500">/mo</span></div>
            <ul className="space-y-1.5 mb-6">
              {plan.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
                  <span className="text-amber-500">✓</span>{f}
                </li>
              ))}
            </ul>
            {subscription?.plan !== key && (
              <form action="/api/subscriptions" method="POST">
                <input type="hidden" name="plan" value={key} />
                <button type="submit" className="w-full py-2.5 px-4 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600">
                  {subscription ? 'Switch to this plan' : 'Choose this plan'}
                </button>
              </form>
            )}
          </Card>
        ))}
      </div>
    </div>
  )
}
