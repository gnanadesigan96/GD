const ONFIDO_BASE_URL = 'https://api.eu.onfido.com/v3.6'

async function onfidoFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${ONFIDO_BASE_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Token token=${process.env.ONFIDO_API_KEY}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  if (!res.ok) {
    const error = await res.text()
    throw new Error(`Onfido API error: ${error}`)
  }
  return res.json()
}

export async function createApplicant(data: {
  firstName: string
  lastName: string
  email: string
}) {
  return onfidoFetch('/applicants', {
    method: 'POST',
    body: JSON.stringify({
      first_name: data.firstName,
      last_name: data.lastName,
      email: data.email,
    }),
  })
}

export async function createCheck(applicantId: string) {
  return onfidoFetch('/checks', {
    method: 'POST',
    body: JSON.stringify({
      applicant_id: applicantId,
      report_names: ['document', 'identity_enhanced'],
    }),
  })
}

export async function getCheckResult(checkId: string) {
  const check = await onfidoFetch(`/checks/${checkId}`)
  return check.result as 'clear' | 'consider' | 'unidentified' | null
}

export async function generateSdkToken(applicantId: string) {
  return onfidoFetch('/sdk_token', {
    method: 'POST',
    body: JSON.stringify({
      applicant_id: applicantId,
      referrer: process.env.NEXTAUTH_URL + '/*',
    }),
  })
}
