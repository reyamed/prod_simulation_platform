FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies (development mode)
RUN npm install

# Copy source code
COPY . .

# Expose Vite default port
EXPOSE 5173

# Run vite server
CMD ["npm", "run", "dev"]
