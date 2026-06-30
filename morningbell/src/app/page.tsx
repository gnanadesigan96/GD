import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-amber-50 to-white">
      <nav className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <span className="text-3xl">🔔</span>
          <span className="text-2xl font-bold text-amber-600">MorningBell</span>
        </div>
        <div className="flex gap-3">
          <Link href="/login" className="px-4 py-2 text-sm font-medium text-amber-700 hover:text-amber-900">
            Sign in
          </Link>
          <Link href="/register" className="px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600">
            Get started
          </Link>
        </div>
      </nav>

      <section className="text-center px-8 py-20 max-w-4xl mx-auto">
        <div className="inline-block bg-amber-100 text-amber-700 px-4 py-1.5 rounded-full text-sm font-medium mb-6">
          Trusted care companions for your loved ones
        </div>
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
          You can't be there every morning.
          <span className="text-amber-500"> We are.</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          Trained care companions call your elderly parent every morning — tracking medications,
          lifting spirits, and sending you a daily update. From $99/month.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/register" className="px-8 py-4 text-base font-semibold bg-amber-500 text-white rounded-xl hover:bg-amber-600 shadow-lg shadow-amber-200">
            Start free 2-week trial
          </Link>
          <Link href="#how-it-works" className="px-8 py-4 text-base font-semibold text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50">
            How it works
          </Link>
        </div>
      </section>

      <section id="how-it-works" className="py-16 px-8 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">How it works</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {[
            { step: '1', icon: '📝', title: 'Register & tell us about your parent', desc: 'Share their needs, language, and preferred time.' },
            { step: '2', icon: '✅', title: 'Choose your plan', desc: 'Companion, Caretaker, or Premium — start with a free trial.' },
            { step: '3', icon: '🤝', title: 'We assign a verified companion', desc: 'Language-matched, background-checked, and trained.' },
            { step: '4', icon: '🔔', title: 'Every morning, they connect', desc: 'You get a daily update. Your parent gets a friend.' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center text-2xl mx-auto mb-4">
                {item.icon}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 px-8 max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">Simple, honest pricing</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { name: 'Companion', price: 99, desc: 'Daily conversations & emotional support', features: ['Daily messaging', '3 calls/week (30 min)', 'Weekly family report'] },
            { name: 'Caretaker', price: 199, desc: 'Health monitoring & medication tracking', features: ['Daily calls', 'Medication tracking', 'Daily family report', 'Emergency escalation'], popular: true },
            { name: 'Premium', price: 349, desc: 'Complete care & unlimited access', features: ['Unlimited video & voice calls', 'Health tracking', 'Priority assignment', 'Real-time updates'] },
          ].map((plan) => (
            <div key={plan.name} className={`rounded-2xl p-8 border-2 ${plan.popular ? 'border-amber-500 bg-amber-50' : 'border-gray-100 bg-white'}`}>
              {plan.popular && <div className="text-xs font-bold text-amber-600 mb-2 uppercase tracking-wide">Most popular</div>}
              <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
              <p className="text-sm text-gray-600 mt-1 mb-4">{plan.desc}</p>
              <div className="text-4xl font-bold text-gray-900 mb-6">${plan.price}<span className="text-base font-normal text-gray-500">/mo</span></div>
              <ul className="space-y-2 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className="text-amber-500">✓</span> {f}
                  </li>
                ))}
              </ul>
              <Link href="/register" className={`block text-center py-3 px-6 rounded-xl font-medium text-sm ${plan.popular ? 'bg-amber-500 text-white hover:bg-amber-600' : 'bg-white border border-amber-300 text-amber-700 hover:bg-amber-50'}`}>
                Start free trial
              </Link>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-gray-100 py-8 px-8 text-center text-sm text-gray-500">
        <p>© 2025 MorningBell. Companionship and care coordination services. Not a medical provider.</p>
      </footer>
    </main>
  )
}
