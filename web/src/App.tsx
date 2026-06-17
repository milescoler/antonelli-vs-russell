import { HashRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { TeamPage } from './pages/TeamPage'
import { MethodPage } from './pages/MethodPage'

function Nav() {
  const link = ({ isActive }: { isActive: boolean }) =>
    'text-sm transition ' + (isActive ? 'text-white' : 'text-zinc-400 hover:text-zinc-200')
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/60 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <NavLink to="/" className="text-sm font-bold tracking-tight text-white">
          Driver<span className="text-sky-400">vs</span>Car
          <span className="ml-2 text-xs font-normal text-zinc-500">F1 2026</span>
        </NavLink>
        <nav className="flex items-center gap-4">
          <NavLink to="/" className={link} end>
            Teams
          </NavLink>
          <NavLink to="/method" className={link}>
            Method
          </NavLink>
        </nav>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-16 border-t border-zinc-800/80">
      <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-zinc-600">
        Teammate-controlled analysis · real qualifying & race data via FastF1 · not affiliated
        with Formula 1. Built by Cole Richards.
      </div>
    </footer>
  )
}

export function App() {
  return (
    <HashRouter>
      <div className="min-h-screen text-zinc-200">
        <Nav />
        <main className="mx-auto max-w-5xl px-4 py-8">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/team/:slug" element={<TeamPage />} />
            <Route path="/method" element={<MethodPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </HashRouter>
  )
}
