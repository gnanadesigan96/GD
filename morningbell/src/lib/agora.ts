import { RtcTokenBuilder, RtcRole } from 'agora-access-token'

export function generateAgoraToken(channelName: string, uid: number): string {
  const appId = process.env.AGORA_APP_ID!
  const appCertificate = process.env.AGORA_APP_CERTIFICATE!
  const expirationTimeInSeconds = 3600
  const currentTimestamp = Math.floor(Date.now() / 1000)
  const privilegeExpiredTs = currentTimestamp + expirationTimeInSeconds

  return RtcTokenBuilder.buildTokenWithUid(
    appId,
    appCertificate,
    channelName,
    uid,
    RtcRole.PUBLISHER,
    privilegeExpiredTs
  )
}

export function generateChannelName(assignmentId: string): string {
  return `mb_${assignmentId}_${Date.now()}`
}
