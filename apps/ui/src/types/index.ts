export interface Agent {
  id: string
  name: string
  description: string
  status: 'active' | 'inactive' | 'error'
}

export interface ContentItem {
  id: string
  title: string
  content: string
  createdAt: string
}

export interface CatalogEntry {
  id: string
  name: string
  description: string
  version: string
}
