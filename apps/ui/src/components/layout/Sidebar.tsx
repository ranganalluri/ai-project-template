
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { navItems } from '@/components/common/navItems';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  // navItems imported from common/navItems.ts
  return (
    <aside className="bg-gray-100 w-64 p-4 min-h-screen">
      <nav className="space-y-2">
        <h3 className="font-bold text-lg mb-4">Navigation</h3>
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`block px-4 py-2 rounded transition ${location.pathname === item.to ? 'bg-gray-300 font-semibold' : 'hover:bg-gray-200'}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
};
