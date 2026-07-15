import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AppLayout from './components/layout/AppLayout'
import AdminLayout from './components/layout/AdminLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import ChangePassword from './pages/profile/ChangePassword'
import Dashboard from './pages/admin/Dashboard'
import DocumentList from './pages/admin/DocumentList'
import UserManagement from './pages/admin/UserManagement'
import ModelSettings from './pages/admin/ModelSettings'

function App() {
  const { isAuthenticated, user } = useAuthStore()

  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/chat" /> : <Login />
      } />
      <Route path="/register" element={
        isAuthenticated ? <Navigate to="/chat" /> : <Register />
      } />

      {/* 受保护路由 - 普通用户 */}
      <Route path="/" element={
        isAuthenticated ? <AppLayout /> : <Navigate to="/login" />
      }>
        <Route index element={<Navigate to="/chat" />} />
        <Route path="chat" element={<Chat />} />
        <Route path="chat/:sessionId" element={<Chat />} />
        <Route path="profile/change-password" element={<ChangePassword />} />
      </Route>

      {/* 受保护路由 - 管理员 */}
      <Route path="/admin" element={
        isAuthenticated && user?.role === 'admin'
          ? <AdminLayout />
          : <Navigate to="/chat" />
      }>
        <Route index element={<Dashboard />} />
        <Route path="documents" element={<DocumentList />} />
        <Route path="users" element={<UserManagement />} />
        <Route path="models" element={<ModelSettings />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<Navigate to="/chat" />} />
    </Routes>
  )
}

export default App
