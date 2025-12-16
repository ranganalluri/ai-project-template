import React from 'react'

export const Sidebar: React.FC = () => {
  return (
    <aside className="bg-gray-100 w-64 p-4 min-h-screen">
      <nav className="space-y-2">
        <h3 className="font-bold text-lg mb-4">Navigation</h3>
        <a
          href="/"
          className="block px-4 py-2 rounded hover:bg-gray-200 transition"
        >
          Dashboard
        </a>
        <a
          href="/agents"
          className="block px-4 py-2 rounded hover:bg-gray-200 transition"
        >
          Agents
        </a>
        <a
          href="/content"
          className="block px-4 py-2 rounded hover:bg-gray-200 transition"
        >
          Content
        </a>
        <a
          href="/catalog"
          className="block px-4 py-2 rounded hover:bg-gray-200 transition"
        >
          Catalog
        </a>
      </nav>
    </aside>
  )
}
