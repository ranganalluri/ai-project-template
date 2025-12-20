
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { navItems } from '@/components/common/navItems';

export const Header: React.FC = () => {
  const location = useLocation();
  return (
    <header className="bg-primary-900 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold">🤖 Agentic AI</h1>
        </div>
        <nav className="flex gap-6">
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`hover:text-primary-100 transition ${location.pathname === item.to ? 'underline font-semibold' : ''}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
};
