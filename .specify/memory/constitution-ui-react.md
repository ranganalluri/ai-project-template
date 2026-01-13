# React UI Project Constitution

**Reference**: See `constitution.md` for core principles  
**Last Updated**: 2025-01-13  
**Scope**: React UI project (`apps/ui/` + `apps/ui-lib/`)

## Service Definition

The UI project provides a **responsive, accessible web application** with shared components:
- **Main App**: React 18, TypeScript 5.0+, Vite (`apps/ui/`)
- **Component Library**: Shared reusable components (`apps/ui-lib/`)
- **Styling**: Tailwind CSS with custom theme
- **Deployment**: Azure Container Apps (static site via nginx)
- **State Management**: React hooks (context API)
- **Testing**: Vitest + React Testing Library

## Project Structure

```
apps/ui/                          # Main React application
├── src/
│   ├── main.tsx                  # React entry point
│   ├── App.tsx                   # Root component with routing
│   ├── pages/                    # Page components (one per route)
│   │   ├── HomePage.tsx
│   │   ├── AgentsPage.tsx
│   │   ├── DocumentsPage.tsx
│   │   └── UserProfilePage.tsx
│   ├── components/               # Page-specific components
│   │   ├── Header.tsx
│   │   ├── Navigation.tsx
│   │   ├── AgentCard.tsx
│   │   └── DocumentUploader.tsx
│   ├── hooks/                    # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useApi.ts
│   │   ├── useFormValidation.ts
│   │   └── useLocalStorage.ts
│   ├── services/                 # API clients & utilities
│   │   ├── api.ts                # Axios configuration
│   │   ├── userService.ts
│   │   ├── agentService.ts
│   │   └── documentService.ts
│   ├── types/                    # TypeScript definitions
│   │   ├── api.types.ts          # API response/request types
│   │   ├── auth.types.ts
│   │   └── domain.types.ts
│   ├── styles/                   # CSS and Tailwind
│   │   └── globals.css
│   ├── utils/                    # Utility functions
│   │   ├── formatting.ts
│   │   ├── validation.ts
│   │   └── constants.ts
│   └── __tests__/                # Component tests
│       ├── HomePage.test.tsx
│       └── components/
├── public/                       # Static assets
│   ├── env-config.js             # Runtime configuration
│   └── favicon.ico
├── vite.config.ts                # Vite build config
├── vitest.config.ts              # Vitest config
├── tsconfig.json                 # TypeScript config
├── tailwind.config.js            # Tailwind configuration
├── package.json                  # Dependencies
└── Dockerfile                    # Container build

apps/ui-lib/                      # Shared component library
├── src/
│   ├── index.ts                  # Public exports
│   ├── components/               # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Toast.tsx
│   │   └── Card.tsx
│   ├── api/                      # Shared API utilities
│   │   ├── client.ts
│   │   └── interceptors.ts
│   ├── hooks/                    # Shared hooks
│   │   ├── useHttp.ts
│   │   └── usePagination.ts
│   ├── types/                    # Shared TypeScript types
│   │   ├── index.ts
│   │   └── api.types.ts
│   ├── utils/                    # Shared utilities
│   │   ├── formatting.ts
│   │   └── validation.ts
│   └── style.css                 # Tailwind CSS
├── tsup.config.ts                # Library build config
├── vite.config.ts                # Vite config
├── vitest.config.ts              # Vitest config
├── package.json                  # Dependencies
└── README.md
```

## Naming Conventions

### TypeScript/React Files
- **Components**: `PascalCase.tsx` (functional components)
  - Example: `HomePage.tsx`, `UserCard.tsx`, `Modal.tsx`
- **Utilities/Services**: `camelCase.ts` (functions and utilities)
  - Example: `userService.ts`, `formatDate.ts`, `validation.ts`
- **Types/Interfaces**: `camelCase.types.ts` (grouped by domain)
  - Example: `api.types.ts`, `auth.types.ts`
- **Constants**: `camelCase.ts` with `UPPER_SNAKE_CASE` values
  - Example: `const API_BASE_URL = "..."`

### JavaScript Variable Naming
- **Variables/Functions**: `camelCase`
  - Example: `const userName = "Jane"`, `function calculateTotal() {}`
- **Classes**: `PascalCase` (rare in React)
  - Example: `class ApiClient {}`
- **Constants**: `UPPER_SNAKE_CASE`
  - Example: `const MAX_FILE_SIZE = 10 * 1024 * 1024`

### API Integration
- **Request bodies**: `camelCase` (matches API format)
- **Response objects**: `camelCase` (from API)
- **TypeScript types**: Match API exactly

```typescript
// ✅ Correct: Matches API camelCase
interface UserResponse {
  userId: string;
  firstName: string;
  lastName: string;
  emailAddress: string;
  createdAt: string;
}

// Usage in component
const response = await fetch("/api/users/123");
const user: UserResponse = await response.json();
console.log(user.firstName);  // ✅ Matches API response
```

## UI Component Library (ui-lib)

### Export Pattern
All public components MUST be exported from `src/index.ts`:

```typescript
// ui-lib/src/index.ts
export { Button } from "./components/Button";
export { Input } from "./components/Input";
export { Modal } from "./components/Modal";
export { Toast } from "./components/Toast";
export { Card } from "./components/Card";

export type { ButtonProps } from "./components/Button";
export type { InputProps } from "./components/Input";
export type { ModalProps } from "./components/Modal";
```

### Component Development Pattern
```typescript
// ui-lib/src/components/Button.tsx
import React from "react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  isLoading = false,
  children,
  disabled,
  ...props
}) => {
  const variants = {
    primary: "bg-blue-500 text-white hover:bg-blue-600",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300",
    danger: "bg-red-500 text-white hover:bg-red-600"
  };

  const sizes = {
    sm: "px-2 py-1 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg"
  };

  return (
    <button
      className={`rounded font-semibold ${variants[variant]} ${sizes[size]} ${
        disabled || isLoading ? "opacity-50 cursor-not-allowed" : ""
      }`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? "Loading..." : children}
    </button>
  );
};
```

### Using ui-lib in apps/ui
```typescript
// apps/ui/src/components/Header.tsx
import { Button } from "@ui-lib";  // Import from shared library

export const Header: React.FC = () => {
  return (
    <header className="bg-white shadow">
      <div className="flex justify-between items-center p-4">
        <h1>AI Project</h1>
        <Button variant="primary" size="md">
          Sign Out
        </Button>
      </div>
    </header>
  );
};
```

## API Client Setup

### Axios Client
```typescript
// apps/ui/src/services/api.ts
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
});

// Add authentication token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login on unauthorized
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

### Service Pattern
```typescript
// apps/ui/src/services/userService.ts
import { apiClient } from "./api";
import { UserResponse, UserListResponse } from "../types/api.types";

export const userService = {
  async getUser(userId: string): Promise<UserResponse> {
    const { data } = await apiClient.get<UserResponse>(`/users/${userId}`);
    return data;
  },

  async listUsers(
    page: number = 1,
    pageSize: number = 10
  ): Promise<UserListResponse> {
    const { data } = await apiClient.get<UserListResponse>("/users", {
      params: { page, page_size: pageSize }
    });
    return data;
  },

  async createUser(
    firstName: string,
    lastName: string,
    emailAddress: string
  ): Promise<UserResponse> {
    const { data } = await apiClient.post<UserResponse>("/users", {
      firstName,
      lastName,
      emailAddress
    });
    return data;
  }
};
```

### Custom Hook Pattern
```typescript
// apps/ui/src/hooks/useApi.ts
import { useState, useEffect } from "react";

export function useApi<T>(
  fn: () => Promise<T>,
  dependencies: unknown[] = []
): { data: T | null; loading: boolean; error: Error | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const result = await fn();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setLoading(false);
      }
    })();
  }, dependencies);

  return { data, loading, error };
}

// Usage in component
function UserProfile({ userId }: { userId: string }) {
  const { data: user, loading, error } = useApi(
    () => userService.getUser(userId),
    [userId]
  );

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!user) return <div>No user found</div>;

  return (
    <div>
      <h1>{user.firstName} {user.lastName}</h1>
      <p>{user.emailAddress}</p>
    </div>
  );
}
```

## Component Development

### Functional Component Pattern
```typescript
// apps/ui/src/components/UserCard.tsx
import React from "react";
import { Button } from "@ui-lib";  // From shared library
import { UserResponse } from "../types/api.types";

interface UserCardProps {
  user: UserResponse;
  onSelect?: (userId: string) => void;
}

export const UserCard: React.FC<UserCardProps> = ({ user, onSelect }) => {
  return (
    <div className="p-4 border rounded-lg hover:shadow-lg">
      <h2 className="text-lg font-bold">
        {user.firstName} {user.lastName}
      </h2>
      <p className="text-gray-600">{user.emailAddress}</p>
      <p className="text-sm text-gray-500">
        Created: {new Date(user.createdAt).toLocaleDateString()}
      </p>
      {onSelect && (
        <Button
          variant="primary"
          size="md"
          onClick={() => onSelect(user.userId)}
          className="mt-2"
        >
          View Profile
        </Button>
      )}
    </div>
  );
};
```

### Page Component Pattern
```typescript
// apps/ui/src/pages/UserListPage.tsx
import React from "react";
import { Button } from "@ui-lib";
import { UserCard } from "../components/UserCard";
import { useApi } from "../hooks/useApi";
import { userService } from "../services/userService";

export const UserListPage: React.FC = () => {
  const [page, setPage] = React.useState(1);
  const { data: userList, loading, error } = useApi(
    () => userService.listUsers(page, 10),
    [page]
  );

  if (loading) return <div>Loading users...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!userList) return <div>No users found</div>;

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-6">Users</h1>
      <div className="grid grid-cols-1 gap-4">
        {userList.users.map((user) => (
          <UserCard
            key={user.userId}
            user={user}
            onSelect={(id) => console.log("Selected:", id)}
          />
        ))}
      </div>
      <div className="flex justify-between mt-6">
        <Button
          onClick={() => setPage(Math.max(1, page - 1))}
          disabled={!userList.hasPreviousPage}
        >
          Previous
        </Button>
        <span>Page {page} of {userList.totalPages}</span>
        <Button
          onClick={() => setPage(page + 1)}
          disabled={!userList.hasNextPage}
        >
          Next
        </Button>
      </div>
    </div>
  );
};
```

## Testing

### Component Tests
```typescript
// apps/ui/src/components/__tests__/UserCard.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UserCard } from "../UserCard";
import { UserResponse } from "../../types/api.types";

describe("UserCard", () => {
  const mockUser: UserResponse = {
    userId: "123",
    firstName: "Jane",
    lastName: "Doe",
    emailAddress: "jane@example.com",
    phoneNumber: null,
    accountStatus: "active",
    createdAt: "2025-01-13T10:00:00Z",
    updatedAt: "2025-01-13T10:00:00Z"
  };

  it("renders user information", () => {
    render(<UserCard user={mockUser} />);
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("jane@example.com")).toBeInTheDocument();
  });

  it("calls onSelect when button clicked", async () => {
    const onSelect = vi.fn();
    render(<UserCard user={mockUser} onSelect={onSelect} />);

    const button = screen.getByRole("button", { name: /view profile/i });
    await userEvent.click(button);

    expect(onSelect).toHaveBeenCalledWith("123");
  });
});
```

### UI Library Component Tests
```typescript
// apps/ui-lib/src/components/__tests__/Button.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "../Button";

describe("Button", () => {
  it("renders with text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
  });

  it("calls onClick handler", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);

    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalled();
  });

  it("disables when disabled prop is true", () => {
    render(<Button disabled>Click</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

## TypeScript Configuration

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "strictNullChecks": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@ui-lib": ["../ui-lib/src/index.ts"],
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@hooks/*": ["./src/hooks/*"],
      "@services/*": ["./src/services/*"],
      "@types/*": ["./src/types/*"]
    }
  },
  "include": ["src"],
  "exclude": ["node_modules"]
}
```

## Styling with Tailwind CSS

### Tailwind Configuration
```javascript
// apps/ui/tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "../ui-lib/src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0066cc",
        secondary: "#666666"
      }
    }
  },
  plugins: []
};
```

### Tailwind in Components
```typescript
// ✅ Use Tailwind classes
export const Card: React.FC<CardProps> = ({ children, className }) => {
  return (
    <div className={`p-4 border rounded-lg shadow ${className}`}>
      {children}
    </div>
  );
};

// ✅ Use CSS modules if needed
import styles from "./Card.module.css";

export const CardWithModule: React.FC = ({ children }) => {
  return <div className={styles.card}>{children}</div>;
};
```

## Development Commands

```bash
# Install dependencies (from project root)
npm ci

# Run UI dev server (http://localhost:5173)
npm -w apps/ui run dev

# Build ui-lib
npm -w apps/ui-lib run build

# Run all tests
npm test

# Run specific test file
npm test -- UserCard.test.tsx

# Type checking
npm run type-check

# Linting & formatting
npm run lint
npm run format

# Build UI for production
npm run build

# Preview production build
npm run preview
```

## Environment Variables

### .env.local (apps/ui)
```bash
# API endpoint
VITE_API_URL=http://localhost:8000/api

# Azure Entra ID
VITE_ENTRA_TENANT_ID=your-tenant-id
VITE_ENTRA_CLIENT_ID=your-client-id

# Feature flags
VITE_ENABLE_AGENTS=true
VITE_ENABLE_DOCUMENTS=true
```

## Security Best Practices

### Authentication Flow
1. User logs in via Azure Entra ID
2. Receive authentication token
3. Store token securely (localStorage for simplicity, sessionStorage better)
4. Include token in API requests (Authorization header)
5. Handle 401 responses (token expired, redirect to login)

### Content Security Policy
```html
<!-- index.html -->
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline';"
/>
```

### Secure Storage Patterns
```typescript
// ✅ Store tokens securely
const storeToken = (token: string) => {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("auth_token", token);
  }
};

// ✅ Clear on logout
const clearToken = () => {
  sessionStorage.removeItem("auth_token");
  localStorage.removeItem("auth_token");
};

// ✅ Retrieve with fallback
const getToken = () => {
  return (
    sessionStorage.getItem("auth_token") ||
    localStorage.getItem("auth_token")
  );
};
```

## Deployment

### Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

### nginx.conf
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        access_log off;
        return 200 "OK";
    }
}
```

## Resources

- **React Docs**: https://react.dev/
- **TypeScript Docs**: https://www.typescriptlang.org/
- **Vite Docs**: https://vitejs.dev/
- **Tailwind CSS**: https://tailwindcss.com/
- **Vitest**: https://vitest.dev/
- **Testing Library**: https://testing-library.com/

---

**Version**: 1.0  
**Created**: 2025-01-13  
**Parent**: [constitution.md](constitution.md)
