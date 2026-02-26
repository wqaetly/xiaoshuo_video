import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import ProjectsPage from './pages/ProjectsPage'
import ScenesPage from './pages/ScenesPage'
import CharactersPage from './pages/CharactersPage'
import GenerationPage from './pages/GenerationPage'
import PreviewPage from './pages/PreviewPage'
import SettingsPage from './pages/SettingsPage'
import TasksPage from './pages/TasksPage'
import EditorPage from './pages/EditorPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectName/scenes" element={<ScenesPage />} />
        <Route path="projects/:projectName/characters" element={<CharactersPage />} />
        <Route path="projects/:projectName/generation" element={<GenerationPage />} />
        <Route path="projects/:projectName/preview" element={<PreviewPage />} />
        <Route path="projects/:projectName/editor" element={<EditorPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App

