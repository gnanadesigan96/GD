import type { User, Elder, Companion, ServiceRequest, Assignment, Subscription, Message, DailyLog, CallSession, PrivacyViolation, Notification } from '@prisma/client'

export type { User, Elder, Companion, ServiceRequest, Assignment, Subscription, Message, DailyLog, CallSession, PrivacyViolation, Notification }

export type UserWithCompanion = User & { companion: Companion | null }
export type AssignmentWithDetails = Assignment & {
  request: ServiceRequest & { elder: Elder }
  companion: Companion & { user: User }
}
export type MessageWithSender = Message & { sender: User }
export type DailyLogWithCompanion = DailyLog & { companion: Companion & { user: User } }

export type ServiceParameterValue = string | string[]

export interface OnboardingStep {
  step: number
  title: string
  description: string
}

export interface AvailabilitySlot {
  day: string
  startTime: string
  endTime: string
}
