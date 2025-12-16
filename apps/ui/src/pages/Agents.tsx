import React from 'react'
import { Card } from '@/components/common/Card'

export const Agents: React.FC = () => {
  return (
    <main className="flex-1 p-8">
      <Card title="Agents Management">
        <p className="text-gray-700">Manage your AI agents here.</p>
      </Card>
    </main>
  )
}
