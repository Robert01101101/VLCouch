import { useState } from 'react'
import { Routes, Route, useLocation, Link } from 'react-router-dom'
import Home from './pages/Home'
import ShowDetail from './pages/ShowDetail'
import Settings from './pages/Settings'
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
      const status = await waitForScanComplete()
      setRefreshKey((key) => key + 1)
      return status
    } finally {
      setScanning(false)
    }
  }

  const isDevMode = import.meta.env.MODE === 'development' || import.meta.env.APP_ENV === 'development';

  return (
    <div className={isDevMode ? "min-h-screen bg-couch-black" : "min-h-screen bg-couch-black"}>
      <header className="sticky top-0 z-50 bg-black/60 backdrop-blur-md px-6 py-3">
        <div className="flex items-center justify-between gap-6 max-w-[1920px] mx-auto">
          {isHome ? (
            <Link
              to="https://github.com/Robert01101101/VLCouch"
              target="_blank"
              className="flex items-center gap-2"
            >
              <img src="/vlcouch.svg" alt="VLCouch Icon" className="h-6 w-6" />
              <span className="font-bold text-white">VLCouch</span>
              {isDevMode && (
                <span className="ml-2 px-2 py-1 bg-couch-red-dark text-white text-xs rounded">
                  Dev
                </span>
              )}
            </Link>
          ) : (
            <Link
              to="/"
              data-testid="nav-home"
              className="text-sm text-gray-300 hover:text-white transition-colors shrink-0"
            >
              ← Home
              {isDevMode && (
                <span className="ml-2 px-2 py-1 bg-couch-red-dark text-white text-xs rounded">
                  Dev
                </span>
              )}
            </Link>
          )}
          <div className="flex items-center gap-3">
            <Link
              to="/settings"
              data-testid="nav-settings"
              className="text-sm text-gray-300 hover:text-white transition-colors shrink-0"
            >
              Settings
            </Link>
            <SearchBar />
          </div>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home refreshKey={refreshKey} scanning={scanning} onScan={handleScan} />} />
          <Route
            path="/shows/:id"
            element={
              <div className="px-6 max-w-7xl mx-auto py-8">
                <ShowDetail />
              </div>
            }
          />
          <Route
            path="/settings"
            element={
              <div className="px-6 max-w-7xl mx-auto py-8">
                <Settings
                  scanning={scanning}
                  onScan={handleScan}
                  onBrowseRefresh={() => setRefreshKey((key) => key + 1)}
                />
              </div>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
