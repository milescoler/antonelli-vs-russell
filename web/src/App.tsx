import { HashRouter, NavLink, Route, Routes } from 'react-router-dom'
import { RaceDecomp } from './pages/RaceDecomp'
import { About } from './pages/About'
import { StudyLinks } from './components/ui'

function Nav() {
  const link = ({ isActive }: { isActive: boolean }) =>
    'text-xs font-bold uppercase tracking-wider transition ' +
    (isActive ? 'text-white' : 'text-zinc-500 hover:text-zinc-200')
  return (
    <header className="sticky top-0 z-20 border-b border-carbon-line bg-carbon/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <NavLink to="/" className="flex items-center gap-2">
          <span className="h-5 w-1.5 rounded-sm bg-f1-red" />
          <span className="text-base font-black uppercase italic tracking-tight text-white">
            What Won the Race?
          </span>
          <span className="ml-1 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
            F1 2026
          </span>
        </NavLink>
        <nav className="flex items-center gap-5">
          <NavLink to="/" className={link} end>
            Race Win
          </NavLink>
          <NavLink to="/about" className={link}>
            About
          </NavLink>
        </nav>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-16 border-t border-carbon-line">
      <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-zinc-600">
        <div className="mb-2">
          The full driver-vs-car analysis: <StudyLinks className="text-zinc-500" />
        </div>
        Real qualifying, race and points data via FastF1 · not affiliated with Formula 1.
        Built by Cole Richards.
      </div>
    </footer>
  )
}

export function App() {
  return (
    <HashRouter>
      <div className="min-h-screen text-zinc-200">
        <Nav />
        <main className="mx-auto max-w-6xl px-4 py-7">
          <Routes>
            <Route path="/" element={<RaceDecomp />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </HashRouter>
  )
}
