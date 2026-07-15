import { Outlet } from 'react-router-dom'

export default function AppLayout() {
  return (
    <div style={{ height: '100vh', overflow: 'hidden' }}>
      <Outlet />
    </div>
  )
}