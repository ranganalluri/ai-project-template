import React from 'react'
import { Card } from '@/components/common/Card'

export const Content: React.FC = () => {
  return (
    <main className="flex-1 p-8">
      <Card title="Content Management">
        <p className="text-gray-700">Manage your content here.</p>
      </Card>
    </main>
  )
}
