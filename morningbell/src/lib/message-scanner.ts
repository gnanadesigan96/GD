export interface ScanResult {
  isFlagged: boolean
  reason: string | null
}

const PHONE_PATTERNS = [
  /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g,
  /\b\d{10}\b/g,
  /\+91\s?\d{10}/g,
  /\b\d{5}\s\d{5}\b/g,
]

const EMAIL_PATTERN = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g

const SOCIAL_PATTERNS = [
  /@[a-zA-Z0-9_.]{2,}/g,
  /instagram\.com|facebook\.com|twitter\.com|linkedin\.com|snapchat\.com|tiktok\.com/gi,
]

const MESSAGING_PATTERNS = [
  /whatsapp|telegram|signal|wechat|viber|skype|facetime/gi,
]

const ADDRESS_PATTERNS = [
  /\d+\s+[a-zA-Z]+\s+(street|st|avenue|ave|road|rd|lane|ln|drive|dr|court|ct|boulevard|blvd)/gi,
  /\b(plot|flat|door|no\.?)\s*\d+/gi,
]

export function scanMessage(content: string): ScanResult {
  for (const pattern of PHONE_PATTERNS) {
    pattern.lastIndex = 0
    if (pattern.test(content)) {
      return { isFlagged: true, reason: 'Phone number detected' }
    }
  }

  EMAIL_PATTERN.lastIndex = 0
  if (EMAIL_PATTERN.test(content)) {
    return { isFlagged: true, reason: 'Email address detected' }
  }

  for (const pattern of SOCIAL_PATTERNS) {
    pattern.lastIndex = 0
    if (pattern.test(content)) {
      return { isFlagged: true, reason: 'Social media handle or link detected' }
    }
  }

  for (const pattern of MESSAGING_PATTERNS) {
    pattern.lastIndex = 0
    if (pattern.test(content)) {
      return { isFlagged: true, reason: 'External messaging app reference detected' }
    }
  }

  for (const pattern of ADDRESS_PATTERNS) {
    pattern.lastIndex = 0
    if (pattern.test(content)) {
      return { isFlagged: true, reason: 'Physical address detected' }
    }
  }

  return { isFlagged: false, reason: null }
}
