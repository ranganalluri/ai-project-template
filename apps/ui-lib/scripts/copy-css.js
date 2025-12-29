import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const stylePath = path.join(__dirname, '..', 'src', 'style.css');
const distPath = path.join(__dirname, '..', 'dist', 'index.css');

if (fs.existsSync(stylePath)) {
  fs.copyFileSync(stylePath, distPath);
  console.log('✓ Copied style.css to dist/index.css');
} else {
  console.error('✗ style.css not found at', stylePath);
  process.exit(1);
}

