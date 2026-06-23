FROM node:20-alpine AS base
WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY src/ ./src/

EXPOSE 3001
ENV NODE_ENV=production

CMD ["node", "src/index.js"]
