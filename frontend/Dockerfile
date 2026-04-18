FROM node:18-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5173

# Default: dev server with HMR.
# For a production build swap to: npm run build && npx serve -s dist -l 5173
CMD ["npm", "run", "dev"]
