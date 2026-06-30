// Run with: node scripts/create-admin.js
// Creates or promotes a user to ADMIN role

const { PrismaClient } = require('@prisma/client')
const bcrypt = require('bcryptjs')
const readline = require('readline')

const prisma = new PrismaClient()

const rl = readline.createInterface({ input: process.stdin, output: process.stdout })
const ask = (q) => new Promise((res) => rl.question(q, res))

async function main() {
  console.log('\n=== MorningBell Admin Setup ===\n')

  const email = await ask('Admin email: ')
  const existing = await prisma.user.findUnique({ where: { email } })

  if (existing) {
    await prisma.user.update({ where: { email }, data: { role: 'ADMIN' } })
    console.log(`\n✓ User ${email} promoted to ADMIN`)
  } else {
    const name = await ask('Admin name: ')
    const password = await ask('Password (min 8 chars): ')
    const hashed = await bcrypt.hash(password, 12)

    await prisma.user.create({
      data: {
        name,
        email,
        password: hashed,
        role: 'ADMIN',
        language: 'en',
        timezone: 'Asia/Kolkata',
      },
    })
    console.log(`\n✓ Admin user created: ${email}`)
  }

  console.log('You can now log in at /login\n')
  rl.close()
  await prisma.$disconnect()
}

main().catch((e) => { console.error(e); process.exit(1) })
