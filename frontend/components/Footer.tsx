export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-600">
            © 2024 SubtitleAI. Todos os direitos reservados.
          </p>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <a href="/privacy" className="text-gray-600 hover:text-purple-600">
              Privacidade
            </a>
            <a href="/terms" className="text-gray-600 hover:text-purple-600">
              Termos
            </a>
            <a href="/contact" className="text-gray-600 hover:text-purple-600">
              Contato
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}