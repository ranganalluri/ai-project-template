import React from 'react'

export const Header: React.FC = () => {
  return (
    <header className="bg-primary-900 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold">🤖 Agentic AI</h1>
        </div>
        <nav className="flex gap-6">
          <a href="/" className="hover:text-primary-100 transition">
            Home
          </a>
          <a href="/agents" className="hover:text-primary-100 transition">
            Agents
          </a>
          <a href="/content" className="hover:text-primary-100 transition">
            Content
          </a>
          <a href="/catalog" className="hover:text-primary-100 transition">
            Catalog
          </a>
        </nav>
      </div>
    </header>
  )
}
