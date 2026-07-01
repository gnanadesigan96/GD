import { PrismaClient, Role, CompanionStatus, ServiceType, RequestStatus, CallType, CallStatus, ViolationLevel } from '@prisma/client'
import bcrypt from 'bcryptjs'

const prisma = new PrismaClient()

const PLAN_PRICES: Record<string, number> = { COMPANION: 99, CARETAKER: 199, PREMIUM: 349 }

function daysAgo(n: number) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d
}
function hoursAgo(n: number) {
  const d = new Date()
  d.setHours(d.getHours() - n)
  return d
}

async function main() {
  const hash = (p: string) => bcrypt.hash(p, 10)

  // ── Admin ─────────────────────────────────────────────────────────────────
  const admin = await prisma.user.upsert({
    where: { email: 'admin@morningbell.com' },
    update: {},
    create: { email: 'admin@morningbell.com', password: await hash('Admin@1234'), name: 'Admin', role: Role.ADMIN, language: 'en', timezone: 'America/New_York' },
  })

  // ── Family users ──────────────────────────────────────────────────────────
  const priya = await prisma.user.upsert({
    where: { email: 'priya@example.com' },
    update: {},
    create: { email: 'priya@example.com', password: await hash('Family@1234'), name: 'Priya Sharma', role: Role.FAMILY, language: 'en', timezone: 'America/Los_Angeles', createdAt: daysAgo(62) },
  })
  const rajan = await prisma.user.upsert({
    where: { email: 'rajan@example.com' },
    update: {},
    create: { email: 'rajan@example.com', password: await hash('Family@1234'), name: 'Rajan Mehta', role: Role.FAMILY, language: 'hi', timezone: 'America/Chicago', createdAt: daysAgo(45) },
  })
  const anitha = await prisma.user.upsert({
    where: { email: 'anitha@example.com' },
    update: {},
    create: { email: 'anitha@example.com', password: await hash('Family@1234'), name: 'Anitha Krishnan', role: Role.FAMILY, language: 'ta', timezone: 'America/New_York', createdAt: daysAgo(30) },
  })

  // ── Subscriptions ─────────────────────────────────────────────────────────
  const periodEnd = new Date(); periodEnd.setMonth(periodEnd.getMonth() + 1)
  await prisma.subscription.upsert({ where: { userId: priya.id }, update: {}, create: { userId: priya.id, plan: 'PREMIUM' as any, status: 'active', currentPeriodEnd: periodEnd, createdAt: daysAgo(60) } })
  await prisma.subscription.upsert({ where: { userId: rajan.id }, update: {}, create: { userId: rajan.id, plan: 'CARETAKER' as any, status: 'active', currentPeriodEnd: periodEnd, createdAt: daysAgo(43) } })
  await prisma.subscription.upsert({ where: { userId: anitha.id }, update: {}, create: { userId: anitha.id, plan: 'COMPANION' as any, status: 'active', currentPeriodEnd: periodEnd, createdAt: daysAgo(28) } })

  // ── Elders ────────────────────────────────────────────────────────────────
  const elder1 = await prisma.elder.create({ data: { familyId: priya.id, name: 'Kamala Sharma', age: 78, language: 'hi', timezone: 'Asia/Kolkata', healthNotes: 'Mild diabetes, takes insulin. Loves music.' } }).catch(() => null)
  const elder2 = await prisma.elder.create({ data: { familyId: priya.id, name: 'Gopal Sharma', age: 81, language: 'hi', timezone: 'Asia/Kolkata', healthNotes: 'Arthritis in both knees. Enjoys reading.' } }).catch(() => null)
  const elder3 = await prisma.elder.create({ data: { familyId: rajan.id, name: 'Geeta Mehta', age: 74, language: 'hi', timezone: 'Asia/Kolkata', healthNotes: 'Hypertension, daily BP medication.' } }).catch(() => null)
  const elder4 = await prisma.elder.create({ data: { familyId: anitha.id, name: 'Subramanian K.', age: 83, language: 'ta', timezone: 'Asia/Kolkata', healthNotes: 'Hard of hearing. Prefers morning calls.' } }).catch(() => null)

  // ── Companions ────────────────────────────────────────────────────────────
  const meena = await prisma.user.upsert({
    where: { email: 'meena@companion.com' },
    update: {},
    create: { email: 'meena@companion.com', password: await hash('Comp@1234'), name: 'Meena Iyer', role: Role.COMPANION, language: 'ta', timezone: 'Asia/Kolkata', createdAt: daysAgo(70) },
  })
  const suresh = await prisma.user.upsert({
    where: { email: 'suresh@companion.com' },
    update: {},
    create: { email: 'suresh@companion.com', password: await hash('Comp@1234'), name: 'Suresh Babu', role: Role.COMPANION, language: 'hi', timezone: 'Asia/Kolkata', createdAt: daysAgo(50) },
  })
  const lakshmi = await prisma.user.upsert({
    where: { email: 'lakshmi@companion.com' },
    update: {},
    create: { email: 'lakshmi@companion.com', password: await hash('Comp@1234'), name: 'Lakshmi Nair', role: Role.COMPANION, language: 'en', timezone: 'Asia/Kolkata', createdAt: daysAgo(35) },
  })

  const meenaComp = await prisma.companion.upsert({ where: { userId: meena.id }, update: {}, create: { userId: meena.id, bio: 'Retired nurse with 20 years of experience. Passionate about elder care.', languages: ['Tamil', 'English', 'Hindi'], skills: ['Health monitoring', 'Medication tracking', 'Companionship'], idVerified: true, status: CompanionStatus.APPROVED, availability: [{ day: 'Monday', startTime: '08:00', endTime: '18:00' }, { day: 'Wednesday', startTime: '08:00', endTime: '18:00' }, { day: 'Friday', startTime: '08:00', endTime: '18:00' }] } })
  const sureshComp = await prisma.companion.upsert({ where: { userId: suresh.id }, update: {}, create: { userId: suresh.id, bio: 'Social worker and yoga instructor. Love bringing joy to elders.', languages: ['Hindi', 'English'], skills: ['Yoga', 'Activity coaching', 'Companionship', 'Family coordination'], idVerified: true, status: CompanionStatus.APPROVED, availability: [{ day: 'Tuesday', startTime: '09:00', endTime: '17:00' }, { day: 'Thursday', startTime: '09:00', endTime: '17:00' }, { day: 'Saturday', startTime: '10:00', endTime: '14:00' }] } })
  const lakshmiComp = await prisma.companion.upsert({ where: { userId: lakshmi.id }, update: {}, create: { userId: lakshmi.id, bio: 'Psychology graduate with a soft spot for elderly wellness conversations.', languages: ['English', 'Malayalam'], skills: ['Companionship', 'Reading', 'Music'], idVerified: true, status: CompanionStatus.APPROVED, availability: [{ day: 'Monday', startTime: '10:00', endTime: '16:00' }, { day: 'Wednesday', startTime: '10:00', endTime: '16:00' }, { day: 'Friday', startTime: '10:00', endTime: '16:00' }] } })

  // Pending companion
  const pending = await prisma.user.upsert({ where: { email: 'ravi@companion.com' }, update: {}, create: { email: 'ravi@companion.com', password: await hash('Comp@1234'), name: 'Ravi Kumar', role: Role.COMPANION, language: 'hi', timezone: 'Asia/Kolkata', createdAt: daysAgo(3) } })
  await prisma.companion.upsert({ where: { userId: pending.id }, update: {}, create: { userId: pending.id, bio: 'Former teacher, eager to help.', languages: ['Hindi', 'Telugu'], skills: ['Companionship', 'Reading'], idVerified: false, status: CompanionStatus.PENDING, availability: [] } })

  // ── Service Requests & Assignments ───────────────────────────────────────
  if (elder1) {
    const req1 = await prisma.serviceRequest.create({ data: { elderId: elder1.id, serviceType: ServiceType.CARETAKER, parameters: { frequency: 'daily', preferredTime: '08:00' }, status: RequestStatus.ACTIVE, createdAt: daysAgo(58) } })
    const asgn1 = await prisma.assignment.create({ data: { requestId: req1.id, companionId: meenaComp.id, status: RequestStatus.ACTIVE, startDate: daysAgo(55), createdAt: daysAgo(55) } })

    // Calls for elder1 assignment
    for (let i = 55; i > 0; i -= 3) {
      const start = hoursAgo(i * 24)
      const end = new Date(start.getTime() + (25 + Math.floor(Math.random() * 20)) * 60000)
      await prisma.callSession.create({ data: { assignmentId: asgn1.id, agoraChannelName: `ch_${asgn1.id}_${i}`, callType: CallType.VIDEO, scheduledAt: start, startedAt: start, endedAt: end, status: CallStatus.COMPLETED, createdAt: start } })
    }
    // Upcoming call
    const upcomingStart = new Date(); upcomingStart.setHours(upcomingStart.getHours() + 2)
    await prisma.callSession.create({ data: { assignmentId: asgn1.id, agoraChannelName: `ch_${asgn1.id}_upcoming`, callType: CallType.VIDEO, scheduledAt: upcomingStart, status: CallStatus.SCHEDULED } })

    // Daily logs
    const moods = ['Happy', 'Calm', 'Tired', 'Happy', 'Calm', 'Sad', 'Happy']
    for (let i = 0; i < 7; i++) {
      await prisma.dailyLog.create({ data: { assignmentId: asgn1.id, companionId: meenaComp.id, mood: moods[i], medicationTaken: true, content: `Session went well. Kamala was ${moods[i].toLowerCase()} today. We discussed her grandchildren and listened to old film songs. Blood pressure checked — 130/85, within normal range.`, concerns: i === 5 ? 'Mentioned some knee pain today. Suggest family follow up with doctor.' : null, createdAt: daysAgo(i) } })
    }
  }

  if (elder2) {
    const req2 = await prisma.serviceRequest.create({ data: { elderId: elder2.id, serviceType: ServiceType.COMPANION, parameters: { frequency: '3x_week' }, status: RequestStatus.ACTIVE, createdAt: daysAgo(50) } })
    const asgn2 = await prisma.assignment.create({ data: { requestId: req2.id, companionId: lakshmiComp.id, status: RequestStatus.ACTIVE, startDate: daysAgo(47), createdAt: daysAgo(47) } })

    for (let i = 47; i > 0; i -= 4) {
      const start = hoursAgo(i * 24)
      const end = new Date(start.getTime() + (30 + Math.floor(Math.random() * 15)) * 60000)
      await prisma.callSession.create({ data: { assignmentId: asgn2.id, agoraChannelName: `ch_${asgn2.id}_${i}`, callType: CallType.VOICE, scheduledAt: start, startedAt: start, endedAt: end, status: CallStatus.COMPLETED, createdAt: start } })
    }
    for (let i = 0; i < 5; i++) {
      await prisma.dailyLog.create({ data: { assignmentId: asgn2.id, companionId: lakshmiComp.id, mood: ['Happy', 'Calm', 'Happy', 'Tired', 'Calm'][i], medicationTaken: i % 2 === 0, content: `Gopal was in good spirits. We read from his favourite book. He enjoyed sharing stories from his working days.`, createdAt: daysAgo(i) } })
    }
  }

  if (elder3) {
    const req3 = await prisma.serviceRequest.create({ data: { elderId: elder3.id, serviceType: ServiceType.CARETAKER, parameters: { frequency: 'daily' }, status: RequestStatus.ACTIVE, createdAt: daysAgo(42) } })
    const asgn3 = await prisma.assignment.create({ data: { requestId: req3.id, companionId: sureshComp.id, status: RequestStatus.ACTIVE, startDate: daysAgo(40), createdAt: daysAgo(40) } })

    for (let i = 40; i > 0; i -= 3) {
      const start = hoursAgo(i * 24)
      const end = new Date(start.getTime() + (20 + Math.floor(Math.random() * 25)) * 60000)
      await prisma.callSession.create({ data: { assignmentId: asgn3.id, agoraChannelName: `ch_${asgn3.id}_${i}`, callType: CallType.VIDEO, scheduledAt: start, startedAt: start, endedAt: end, status: CallStatus.COMPLETED, createdAt: start } })
    }
    for (let i = 0; i < 6; i++) {
      await prisma.dailyLog.create({ data: { assignmentId: asgn3.id, companionId: sureshComp.id, mood: ['Calm', 'Happy', 'Anxious', 'Calm', 'Happy', 'Calm'][i], medicationTaken: true, content: `Geeta completed her morning yoga stretches. BP checked — normal. She was a bit anxious about an upcoming doctor's visit but felt better after our chat.`, createdAt: daysAgo(i) } })
    }
  }

  if (elder4) {
    const req4 = await prisma.serviceRequest.create({ data: { elderId: elder4.id, serviceType: ServiceType.COMPANION, parameters: { frequency: '3x_week' }, status: RequestStatus.ACTIVE, createdAt: daysAgo(27) } })
    const asgn4 = await prisma.assignment.create({ data: { requestId: req4.id, companionId: meenaComp.id, status: RequestStatus.ACTIVE, startDate: daysAgo(25), createdAt: daysAgo(25) } })

    for (let i = 25; i > 0; i -= 4) {
      const start = hoursAgo(i * 24)
      const end = new Date(start.getTime() + (35 + Math.floor(Math.random() * 10)) * 60000)
      await prisma.callSession.create({ data: { assignmentId: asgn4.id, agoraChannelName: `ch_${asgn4.id}_${i}`, callType: CallType.VOICE, scheduledAt: start, startedAt: start, endedAt: end, status: CallStatus.COMPLETED, createdAt: start } })
    }
    for (let i = 0; i < 4; i++) {
      await prisma.dailyLog.create({ data: { assignmentId: asgn4.id, companionId: meenaComp.id, mood: ['Happy', 'Calm', 'Tired', 'Happy'][i], medicationTaken: true, content: `Subramanian was cheerful this morning. Spoke about his village life. Hearing aid was working well today. Reminded family to schedule ENT appointment.`, createdAt: daysAgo(i) } })
    }
  }

  // ── Team members ──────────────────────────────────────────────────────────
  await prisma.teamMember.upsert({ where: { email: 'ops@morningbell.com' }, update: {}, create: { email: 'ops@morningbell.com', name: 'Deepa Rajan', role: 'Operations Lead', status: 'ACCEPTED', invitedAt: daysAgo(30), acceptedAt: daysAgo(29) } })
  await prisma.teamMember.upsert({ where: { email: 'support@morningbell.com' }, update: {}, create: { email: 'support@morningbell.com', name: 'Karthik M.', role: 'Customer Support', status: 'ACCEPTED', invitedAt: daysAgo(20), acceptedAt: daysAgo(18) } })
  await prisma.teamMember.upsert({ where: { email: 'quality@morningbell.com' }, update: {}, create: { email: 'quality@morningbell.com', name: null, role: 'Quality Reviewer', status: 'PENDING', invitedAt: daysAgo(3) } })

  console.log('✓ Seed complete')
  console.log('  Admin login:  admin@morningbell.com / Admin@1234')
  console.log('  Family login: priya@example.com / Family@1234')
  console.log('  Family login: rajan@example.com / Family@1234')
  console.log('  Family login: anitha@example.com / Family@1234')
}

main().catch(console.error).finally(() => prisma.$disconnect())
