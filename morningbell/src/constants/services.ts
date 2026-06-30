export type ParameterType = 'select' | 'multiselect' | 'text' | 'time' | 'textarea'

export interface ServiceParameter {
  key: string
  label: string
  type: ParameterType
  options?: string[]
  required?: boolean
  placeholder?: string
}

export interface ServiceDefinition {
  type: string
  label: string
  description: string
  icon: string
  parameters: ServiceParameter[]
}

export const SERVICE_DEFINITIONS: ServiceDefinition[] = [
  {
    type: 'COMPANION',
    label: 'Companion',
    description: 'A friendly companion for daily conversations and emotional support',
    icon: '💬',
    parameters: [
      { key: 'language', label: 'Preferred Language', type: 'select', options: ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada'], required: true },
      { key: 'topics', label: 'Favourite Topics', type: 'multiselect', options: ['Religion', 'Sports', 'Family', 'News', 'Music', 'Movies', 'Cooking', 'History'] },
      { key: 'callDuration', label: 'Call Duration', type: 'select', options: ['15 minutes', '30 minutes', '45 minutes', '60 minutes'], required: true },
      { key: 'frequency', label: 'Frequency', type: 'select', options: ['Daily', 'Alternate days', '3x per week', 'Weekdays only'], required: true },
      { key: 'callType', label: 'Call Preference', type: 'select', options: ['Video', 'Audio', 'Either'], required: true },
      { key: 'preferredTime', label: 'Preferred Time (local time)', type: 'time', required: true },
    ],
  },
  {
    type: 'CARETAKER',
    label: 'Caretaker',
    description: 'Health monitoring, medication tracking and care coordination',
    icon: '🏥',
    parameters: [
      { key: 'language', label: 'Preferred Language', type: 'select', options: ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada'], required: true },
      { key: 'medications', label: 'Medications to Track', type: 'textarea', placeholder: 'List medications, dosage and timing...', required: true },
      { key: 'healthConditions', label: 'Health Conditions', type: 'textarea', placeholder: 'Diabetes, hypertension, etc.', required: true },
      { key: 'mobilityLevel', label: 'Mobility Level', type: 'select', options: ['Fully independent', 'Needs some assistance', 'Limited mobility', 'Bedridden'], required: true },
      { key: 'emergencyContact', label: 'Emergency Contact Name & Phone', type: 'text', required: true },
      { key: 'reportFrequency', label: 'Report Frequency', type: 'select', options: ['Daily', 'Every 2 days', 'Weekly'], required: true },
      { key: 'callType', label: 'Call Preference', type: 'select', options: ['Video', 'Audio', 'Either'], required: true },
      { key: 'preferredTime', label: 'Preferred Time (local time)', type: 'time', required: true },
    ],
  },
  {
    type: 'ACTIVITY_COACH',
    label: 'Activity Coach',
    description: 'Guided activities for mental stimulation and physical wellbeing',
    icon: '🧠',
    parameters: [
      { key: 'language', label: 'Preferred Language', type: 'select', options: ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada'], required: true },
      { key: 'interests', label: 'Interests', type: 'multiselect', options: ['Yoga', 'Reading', 'Music', 'Puzzles', 'Cooking', 'Gardening', 'Drawing', 'Meditation'] },
      { key: 'physicalAbility', label: 'Physical Ability', type: 'select', options: ['Full mobility', 'Limited mobility', 'Seated activities only'], required: true },
      { key: 'sessionDuration', label: 'Session Duration', type: 'select', options: ['30 minutes', '45 minutes', '60 minutes'], required: true },
      { key: 'goals', label: 'Goals', type: 'multiselect', options: ['Mental stimulation', 'Physical activity', 'Emotional wellbeing', 'Social connection'] },
      { key: 'frequency', label: 'Frequency', type: 'select', options: ['Daily', 'Alternate days', '3x per week'], required: true },
      { key: 'preferredTime', label: 'Preferred Time (local time)', type: 'time', required: true },
    ],
  },
  {
    type: 'COORDINATOR',
    label: 'Family Coordinator',
    description: 'Regular updates and coordination between your loved one and family',
    icon: '📋',
    parameters: [
      { key: 'language', label: 'Preferred Language', type: 'select', options: ['English', 'Tamil', 'Telugu', 'Hindi', 'Kannada'], required: true },
      { key: 'updateFrequency', label: 'Update Frequency', type: 'select', options: ['Daily', 'Every 2 days', 'Weekly'], required: true },
      { key: 'updateFormat', label: 'Update Format', type: 'multiselect', options: ['In-app', 'Email', 'WhatsApp'] },
      { key: 'recipients', label: 'Family Members to Notify (names)', type: 'text', placeholder: 'John, Sarah, Mike...', required: true },
      { key: 'callType', label: 'Call Preference', type: 'select', options: ['Video', 'Audio', 'Either'], required: true },
      { key: 'preferredTime', label: 'Preferred Time (local time)', type: 'time', required: true },
    ],
  },
]
