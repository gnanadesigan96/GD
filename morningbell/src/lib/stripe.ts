import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2024-04-10',
})

export const PLANS = {
  COMPANION: {
    name: 'Companion',
    price: 99,
    priceId: process.env.STRIPE_PRICE_COMPANION!,
    features: ['Daily messaging', '3 calls per week (30 min each)', 'Weekly family report'],
  },
  CARETAKER: {
    name: 'Caretaker',
    price: 199,
    priceId: process.env.STRIPE_PRICE_CARETAKER!,
    features: ['Daily calls', 'Health & medication tracking', 'Daily family report', 'Emergency escalation'],
  },
  PREMIUM: {
    name: 'Premium',
    price: 349,
    priceId: process.env.STRIPE_PRICE_PREMIUM!,
    features: ['Unlimited calls & video', 'Health tracking', 'Priority assignment', 'Multiple companions', 'Real-time family updates'],
  },
}
