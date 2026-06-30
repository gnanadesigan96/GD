import Link from 'next/link'

const BellIcon = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
)
const ArrowRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
  </svg>
)
const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)
const StarIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
)
const ShieldCheckIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><polyline points="9 12 11 14 15 10" />
  </svg>
)
const GlobeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
)
const ClockIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
)
const FileTextIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
  </svg>
)
const UserPlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><line x1="19" y1="8" x2="19" y2="14" /><line x1="22" y1="11" x2="16" y2="11" />
  </svg>
)
const CreditCardIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
  </svg>
)

const steps = [
  { n: '01', icon: <UserPlusIcon />, title: 'Register & share details', desc: 'Tell us about your loved one — language, schedule, and care needs.' },
  { n: '02', icon: <CreditCardIcon />, title: 'Choose your plan', desc: 'Companion, Caretaker, or Premium. Start with a free 2-week trial.' },
  { n: '03', icon: <ShieldCheckIcon />, title: 'Get matched in 24h', desc: 'We assign a verified, language-matched companion quickly.' },
  { n: '04', icon: <FileTextIcon />, title: 'Daily check-ins begin', desc: 'Your companion calls every morning. You receive a daily report.' },
]

const plans = [
  {
    name: 'Companion',
    price: 99,
    desc: 'Daily conversations & emotional support',
    features: ['Daily messaging', '3 calls/week (30 min each)', 'Weekly family report', 'Language-matched companion'],
    popular: false,
  },
  {
    name: 'Caretaker',
    price: 199,
    desc: 'Health monitoring & medication tracking',
    features: ['Daily voice & video calls', 'Medication tracking', 'Daily family report', 'Emergency escalation', 'Health notes'],
    popular: true,
  },
  {
    name: 'Premium',
    price: 349,
    desc: 'Complete care with unlimited access',
    features: ['Unlimited video & voice calls', 'Full health tracking', 'Priority assignment', 'Multiple companions', 'Real-time family updates'],
    popular: false,
  },
]

const testimonials = [
  { quote: 'My father lights up during his morning calls. The companion speaks Tamil fluently — it feels like family.', name: 'Priya S., San Jose' },
  { quote: 'I used to worry every single day. Now I get a report every morning and I can finally breathe again.', name: 'James K., London' },
  { quote: 'The medication reminders alone are worth it. Mom finally takes her pills on time — every day.', name: 'Anitha R., Toronto' },
]

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white font-sans">
      {/* Navbar */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-100">
        <nav className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-primary-700 rounded-lg flex items-center justify-center text-white">
              <BellIcon />
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">MorningBell</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#how-it-works" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer">How it works</a>
            <a href="#pricing" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer">Pricing</a>
            <Link href="/register/companion" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer">Become a companion</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors cursor-pointer">
              Sign in
            </Link>
            <Link href="/register" className="px-4 py-2.5 text-sm font-semibold bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-all duration-150 shadow-sm cursor-pointer">
              Get started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="pt-20 pb-28 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 px-3.5 py-1.5 rounded-full text-sm font-medium mb-8 border border-primary-100">
              <span className="flex text-accent-500">
                {[...Array(5)].map((_, i) => <StarIcon key={i} />)}
              </span>
              Trusted by 500+ families across US & UK
            </div>
            <h1 className="text-5xl lg:text-6xl font-bold text-slate-900 leading-[1.1] mb-6 tracking-tight">
              You can't be there{' '}
              <span className="text-primary-700">every morning.</span>
              <br />
              <span className="text-accent-500">We are.</span>
            </h1>
            <p className="text-xl text-slate-600 leading-relaxed mb-10 max-w-lg">
              Trained care companions call your elderly parent every morning — tracking medications, lifting spirits, and sending you a daily update.
            </p>
            <div className="flex flex-wrap gap-4 mb-10">
              <Link href="/register" className="inline-flex items-center gap-2 px-7 py-3.5 text-base font-semibold bg-primary-700 text-white rounded-xl hover:bg-primary-800 shadow-lg shadow-primary-100 hover:shadow-xl transition-all duration-200 cursor-pointer">
                Start free 2-week trial
                <ArrowRightIcon />
              </Link>
              <a href="#how-it-works" className="inline-flex items-center gap-2 px-7 py-3.5 text-base font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:border-slate-300 transition-all duration-150 cursor-pointer">
                See how it works
              </a>
            </div>
            <p className="text-sm text-slate-400">No credit card required · Cancel anytime · Plans from $99/month</p>
          </div>

          {/* Visual mockup */}
          <div className="hidden lg:block">
            <div className="relative bg-gradient-to-br from-primary-50 via-white to-accent-50 rounded-3xl p-8 border border-slate-100">
              <div className="bg-white rounded-2xl shadow-card-lg border border-slate-100 p-6 mb-4">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Daily Update</p>
                    <p className="text-sm font-semibold text-slate-900">Rajamma · Today, 9:14 AM</p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-xs font-semibold border border-emerald-100">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    Great mood
                  </span>
                </div>
                <div className="space-y-2.5">
                  {['Medication taken — morning dose', '30 min call completed', 'Ate breakfast, feeling cheerful'].map((item) => (
                    <div key={item} className="flex items-center gap-3 bg-slate-50 rounded-lg px-3 py-2.5">
                      <div className="w-5 h-5 bg-primary-700 rounded-md flex items-center justify-center flex-shrink-0">
                        <CheckIcon />
                      </div>
                      <span className="text-sm text-slate-700">{item}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-4 italic border-t border-slate-50 pt-3">
                  "She was talking about her grandchildren today — very happy and energetic."
                </p>
              </div>
              <div className="flex items-center gap-3 bg-white rounded-xl shadow-card border border-slate-100 px-4 py-3">
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center text-primary-700 font-bold text-sm flex-shrink-0">PK</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900">Priya K.</p>
                  <p className="text-xs text-slate-500">Your companion · Tamil & English</p>
                </div>
                <div className="flex text-accent-500 flex-shrink-0">
                  {[...Array(5)].map((_, i) => <StarIcon key={i} />)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <section className="border-y border-slate-100 bg-slate-50 py-5 px-6">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-center gap-10 text-sm text-slate-500 font-medium">
          <div className="flex items-center gap-2 text-slate-600"><ShieldCheckIcon /><span>ID-verified companions</span></div>
          <div className="flex items-center gap-2 text-slate-600"><GlobeIcon /><span>5 languages supported</span></div>
          <div className="flex items-center gap-2 text-slate-600"><ClockIcon /><span>Timezone-aware scheduling</span></div>
          <div className="flex items-center gap-2 text-slate-600"><FileTextIcon /><span>Daily family reports</span></div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4 tracking-tight">Simple to start. Meaningful every day.</h2>
            <p className="text-lg text-slate-600 max-w-xl mx-auto">Get your loved one connected with a companion in under 24 hours.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {steps.map((step, i) => (
              <div key={step.n} className="relative text-center">
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[calc(50%+2rem)] right-[-50%] h-px border-t-2 border-dashed border-slate-200" />
                )}
                <div className="w-16 h-16 bg-primary-50 border-2 border-primary-100 rounded-2xl flex items-center justify-center text-primary-700 mx-auto mb-4">
                  {step.icon}
                </div>
                <p className="text-xs font-bold text-primary-600 tracking-widest mb-2">{step.n}</p>
                <h3 className="font-semibold text-slate-900 mb-2">{step.title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4 tracking-tight">Simple, honest pricing</h2>
            <p className="text-lg text-slate-600">All plans include a free 2-week trial. No card required. Cancel anytime.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-2xl p-8 relative transition-all duration-150 ${
                  plan.popular
                    ? 'border-2 border-primary-600 bg-white shadow-card-lg'
                    : 'border border-slate-200 bg-white hover:border-slate-300 hover:shadow-card-hover'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                    <span className="bg-primary-700 text-white text-xs font-bold px-4 py-1 rounded-full uppercase tracking-wide">Most popular</span>
                  </div>
                )}
                <h3 className="text-xl font-bold text-slate-900">{plan.name}</h3>
                <p className="text-sm text-slate-500 mt-1 mb-6">{plan.desc}</p>
                <div className="flex items-baseline gap-1 mb-8">
                  <span className="text-4xl font-bold text-slate-900">${plan.price}</span>
                  <span className="text-slate-400 text-sm">/month</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-3 text-sm text-slate-700">
                      <span className="flex-shrink-0 w-5 h-5 bg-primary-50 text-primary-700 rounded-full flex items-center justify-center border border-primary-100">
                        <CheckIcon />
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`block text-center py-3 px-6 rounded-xl font-semibold text-sm transition-all duration-150 cursor-pointer ${
                    plan.popular
                      ? 'bg-primary-700 text-white hover:bg-primary-800 shadow-sm'
                      : 'bg-white border-2 border-slate-200 text-slate-700 hover:border-primary-300 hover:text-primary-700'
                  }`}
                >
                  Start free trial
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4 tracking-tight">Families trust MorningBell</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((t) => (
              <div key={t.name} className="bg-white rounded-2xl border border-slate-100 shadow-card p-8 hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-150">
                <div className="flex text-accent-500 mb-4">
                  {[...Array(5)].map((_, i) => <StarIcon key={i} />)}
                </div>
                <p className="text-slate-700 leading-relaxed mb-6 italic">"{t.quote}"</p>
                <p className="text-sm font-semibold text-slate-900">{t.name}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 bg-primary-700">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4 tracking-tight">Give your parent the connection they deserve</h2>
          <p className="text-primary-200 mb-8 text-lg">Start with a free 2-week trial. No commitment required.</p>
          <Link href="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-primary-700 rounded-xl font-semibold hover:bg-primary-50 shadow-lg transition-all duration-150 cursor-pointer text-base">
            Get started free
            <ArrowRightIcon />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-14 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-start justify-between gap-10 mb-10">
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white">
                  <BellIcon />
                </div>
                <span className="text-lg font-bold text-white">MorningBell</span>
              </div>
              <p className="text-sm text-slate-400 max-w-xs leading-relaxed">Daily care and companionship for your loved ones, wherever they are.</p>
            </div>
            <div className="flex gap-16 text-sm">
              <div className="space-y-3">
                <p className="font-semibold text-white">Product</p>
                <a href="#how-it-works" className="block hover:text-white transition-colors cursor-pointer">How it works</a>
                <a href="#pricing" className="block hover:text-white transition-colors cursor-pointer">Pricing</a>
                <Link href="/register/companion" className="block hover:text-white transition-colors cursor-pointer">Become a companion</Link>
              </div>
              <div className="space-y-3">
                <p className="font-semibold text-white">Account</p>
                <Link href="/login" className="block hover:text-white transition-colors cursor-pointer">Sign in</Link>
                <Link href="/register" className="block hover:text-white transition-colors cursor-pointer">Register</Link>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-6 text-xs text-slate-500">
            © 2025 MorningBell. Companionship and care coordination. Not a medical provider.
          </div>
        </div>
      </footer>
    </main>
  )
}
