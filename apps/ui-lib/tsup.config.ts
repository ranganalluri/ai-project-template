import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  sourcemap: true,
  clean: true,
  outDir: 'dist',
  external: ['react', 'react-dom', 'ol', 'pdfjs-dist'],
  tsconfig: './tsconfig.json',
  // loader: {
  //   '.css': 'copy',
  // },
});
