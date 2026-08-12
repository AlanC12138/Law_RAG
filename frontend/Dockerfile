# node:20-slim (Debian/glibc), NOT alpine (musl), and Node 20 to match
# .github/workflows/frontend-ci.yml. Rollup and esbuild ship per-platform
# native binaries, and npm records only the ones for the platform that
# generated package-lock.json. A lock built on alpine pins
# @rollup/rollup-linux-x64-musl, which then makes `vite build` fail on
# CI's glibc runner with "Cannot find module @rollup/rollup-linux-x64-gnu".
# Keeping dev and CI on the same libc keeps one lock file valid for both.
FROM node:20-slim

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

# Default: dev server with HMR.
# For a production build swap to: npm run build && npx serve -s dist -l 5173
CMD ["npm", "run", "dev"]
