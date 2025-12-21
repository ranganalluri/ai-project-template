
import React from 'react';
// import { Card } from '@/components/common/Card';
// import { Button } from '@agentic/ui-lib';
import { UserList } from '@/components/common/UserList';

export const Home: React.FC = () => {
  // const click = () => {
  //   console.log('Button clicked')
  // }
  return (
    <main className="flex-1 p-8">
      {/* <Card title="Welcome to Agentic AI">
        <p className="text-gray-700 mb-4">
          Agentic AI is a powerful platform for building and deploying AI agents using FastAPI and React.
        </p>
        <p className="text-gray-700 mb-6">
          Use the navigation menu to explore agents, manage content, browse the catalog, and more.
        </p>
        <div className="flex gap-4">
          <Button variant="primary" onClick={click} size="lg">
            Get Started
          </Button>
          <Button variant="secondary" size="lg">
            Learn More
          </Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <Card title="🤖 Agents">
          <p className="text-gray-700">Manage and monitor your AI agents in real-time.</p>
        </Card>
        <Card title="📄 Content">
          <p className="text-gray-700">Create and organize content for your agents to process.</p>
        </Card>
        <Card title="📚 Catalog">
          <p className="text-gray-700">Browse available models and capabilities.</p>
        </Card>
      </div> */}

      <UserList />
    </main>
  );
}
