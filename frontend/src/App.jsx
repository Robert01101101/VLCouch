import { useState } from 'react'
import { Routes, Route, useLocation, Link } from 'react-router-dom'
import Home from './pages/Home'
import ShowDetail from './pages/ShowDetail'
import SearchBar from './components/SearchBar'
import { triggerScan, waitForScanComplete } from './api'

export default function App() {
  const location = useLocation()
  const isHome = location.pathname === '/'
  const [scanning, setScanning] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  async function handleScan() {
    setScanning(true)
    try {
      await triggerScan()
      await waitForScanComplete()
      setRefreshKey((key) => key + 1)
    } catch (e) {
      alert(e.message)
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-couch-black">
      <header className="sticky top-0 z-50 bg-black/60 backdrop-blur-md px-6 py-3">
        <div className="flex items-center justify-between gap-6 max-w-[1920px] mx-auto">
          {isHome ? (
            <button
              data-testid="rescan-library"
              onClick={handleScan}
              disabled={scanning}
              className="text-sm text-gray-300 hover:text-white transition-colors disabled:opacity-50 shrink-0"
            >
              {scanning ? 'Scanning...' : 'Rescan Library'}
            </button>
          ) : (
            <Link
              to="/"
              data-testid="nav-home"
              className="text-sm text-gray-300 hover:text-white transition-colors shrink-0"
            >
              ← Home
            </Link>
          )}
          <SearchBar />
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home refreshKey={refreshKey} />} />
          <Route
            path="/shows/:id"
            element={
              <div className="px-6 max-w-7xl mx-auto py-8">
                <ShowDetail />
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
