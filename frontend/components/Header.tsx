import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { Menu, X, User } from 'lucide-react'
import { useState } from 'react'

export default function Header() {
  const { user, logout } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="bg-white shadow-sm">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="text-2xl font-bold text-purple-600">
              SubtitleAI
            </Link>
          </div>

          {/* Desktop menu */}
          <div className="hidden md:flex items-center space-x-8">
            <Link href="/pricing" className="text-gray-700 hover:text-purple-600">
              Preços
            </Link>
            {user ? (
              <>
                <Link href="/dashboard" className="text-gray-700 hover:text-purple-600">
                  Dashboard
                </Link>
                <div className="flex items-center space-x-4">
                  <span className="text-sm text-gray-500">
                    {user.minutesRemaining} min restantes
                  </span>
                  <button
                    onClick={logout}
                    className="text-gray-700 hover:text-purple-600"
                  >
                    Sair
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link href="/login" className="text-gray-700 hover:text-purple-600">
                  Entrar
                </Link>
                <Link href="/register" className="btn-primary">
                  Começar Grátis
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-gray-700"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 bg-white shadow-lg">
            <Link href="/pricing" className="block px-3 py-2 text-gray-700">
              Preços
            </Link>
            {user ? (
              <>
                <Link href="/dashboard" className="block px-3 py-2 text-gray-700">
                  Dashboard
                </Link>
                <button
                  onClick={logout}
                  className="block w-full text-left px-3 py-2 text-gray-700"
                >
                  Sair
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="block px-3 py-2 text-gray-700">
                  Entrar
                </Link>
                <Link href="/register" className="block px-3 py-2 text-purple-600 font-medium">
                  Começar Grátis
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}