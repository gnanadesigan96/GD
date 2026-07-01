import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { PLANS } from '@/lib/stripe'
import { prisma } from '@/lib/prisma'
import { Badge } from '@/components/ui/Badge'

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)
const StarIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
)
const CreditCardIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
  </svg>
)

const PLAN_ORDER = ['BASIC', 'STANDARD', 'PREMIUM']
const POPULAR_PLAN = 'STANDARD'

export default async function SubscriptionPage() {
  const session = await getServerSession(authOptions)
  const userId = (session!.user as any).id
  const subscription = await prisma.subscription.findUnique({ where: { userId } })

  const planEntries = PLAN_ORDER
    .filter(key => PLANS[key])
    .map(key => [key, PLANS[key]] as [string, typeof PLANS[string]])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Subscription</h2>
        <p className="text-slate-500 mt-0.5 text-sm">Choose the plan that fits your family's needs</p>
      </div>

      {/* Active plan banner */}
      {subscription && (
        <div className="flex items-center justify-between bg-gradient-to-r from-emerald-700 to-emerald-600 rounded-xl p-5 text-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <CreditCardIcon />
            </div>
            <div>
              <p className="font-semibold text-sm">Active plan: {subscription.plan}</p>
              {subscription.currentPeriodEnd && (
                <p className="text-emerald-200 text-xs mt-0.5">
                  Renews {new Date(subscription.currentPeriodEnd).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                </p>
              )}
            </div>
          </div>
          <Badge variant="success">Active</Badge>
        </div>
      )}

      {/* Pricing cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {planEntries.map(([key, plan]) => {
          const isCurrent = subscription?.plan === key
          const isPopular = key === POPULAR_PLAN
          return (
            <div key={key} className={`relative bg-white rounded-2xl border-2 transition-all duration-150 ${isCurrent ? 'border-emerald-400' : isPopular ? 'border-primary-600 shadow-card-lg' : 'border-slate-100 shadow-card'}`}>
              {/* Popular badge */}
              {isPopular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <div className="inline-flex items-center gap-1 bg-primary-700 text-white text-xs font-bold px-3.5 py-1 rounded-full shadow-sm">
                    <StarIcon />
                    Most Popular
                  </div>
                </div>
              )}

              <div className="p-6">
                {isCurrent && (
                  <div className="mb-3">
                    <Badge variant="success">Current plan</Badge>
                  </div>
                )}

                <h3 className="text-lg font-bold text-slate-900">{plan.name}</h3>

                <div className="flex items-end gap-1 my-4">
                  <span className="text-4xl font-bold text-slate-900">${plan.price}</span>
                  <span className="text-slate-500 text-sm mb-1">/month</span>
                </div>

                <ul className="space-y-2.5 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
                      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mt-0.5">
                        <CheckIcon />
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <div className="w-full py-2.5 px-4 bg-slate-100 text-slate-400 rounded-lg text-sm font-semibold text-center">
                    Current plan
                  </div>
                ) : (
                  <form action="/api/subscriptions" method="POST">
                    <input type="hidden" name="plan" value={key} />
                    <button
                      type="submit"
                      className={`w-full py-2.5 px-4 rounded-lg text-sm font-semibold transition-all duration-150 cursor-pointer ${isPopular ? 'bg-primary-700 text-white hover:bg-primary-800' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                    >
                      {subscription ? 'Switch to this plan' : 'Choose this plan'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <p className="text-xs text-slate-400 text-center">
        All plans include a 14-day free trial. Cancel anytime. Not a medical provider.
      </p>
    </div>
  )
}
