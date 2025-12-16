import React from 'react'
import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { Home } from '@/pages/Home'
import { Agents } from '@/pages/Agents'
import { Content } from '@/pages/Content'
import { Catalog } from '@/pages/Catalog'
import '@/styles/index.css'

type Page = 'home' | 'agents' | 'content' | 'catalog'

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = React.useState<Page>('home')

  // Simple routing based on hash
  React.useEffect(() => {
    const handleHashChange = () => {
      const page = window.location.hash.slice(1) as Page
      if (['home', 'agents', 'content', 'catalog'].includes(page)) {
        setCurrentPage(page)
      }
    }

    window.addEventListener('hashchange', handleHashChange)
    handleHashChange()

    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const renderPage = () => {
    switch (currentPage) {
      case 'agents':
        return <Agents />
      case 'content':
        return <Content />
      case 'catalog':
        return <Catalog />
      case 'home':
      default:
        return <Home />
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        {renderPage()}
      </div>
    </div>
  )
}

export default App
