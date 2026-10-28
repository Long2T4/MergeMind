import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import HistoryPage from './pages/HistoryPage'
import HomePage from './pages/HomePage'
import LearningPage from './pages/LearningPage'
import NewReviewPage from './pages/NewReviewPage'
import NotFoundPage from './pages/NotFoundPage'
import ProjectsPage from './pages/ProjectsPage'
import ReviewResultsPage from './pages/ReviewResultsPage'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="reviews/new" element={<NewReviewPage />} />
        <Route path="reviews/:reviewId" element={<ReviewResultsPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App
