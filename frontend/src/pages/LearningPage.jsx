import LegacyLearningPage from './LegacyLearningPage'
import LearningDashboard from '../stage12/LearningDashboard'

// One learning page: the existing profile, plus how you marked each finding.
export default function LearningPage() {
  return <LegacyLearningPage outcomes={<LearningDashboard />} />
}
