import React from 'react'
import { Card } from '@/components/common/Card'

export const Catalog: React.FC = () => {
  return (
    <main className="flex-1 p-8">
      <Card title="Catalog Browser">
        <p className="text-gray-700">Browse available models and capabilities.</p>
      </Card>
    </main>
  )
}
