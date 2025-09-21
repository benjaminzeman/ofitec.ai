# Frontend Next.js
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build
EXPOSE 3001
CMD ["npm", "run", "start"]
