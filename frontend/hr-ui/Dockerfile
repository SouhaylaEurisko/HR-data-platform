# ── Stage 1: Build the React app ──
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files first (for Docker layer caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the source code
COPY . .

# Build argument for the backend API URL
ARG VITE_API_BASE_URL=http://localhost:4533
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build the production bundle
RUN npm run build

# ── Stage 2: Serve with nginx ──
FROM nginx:alpine

# Copy the built files to nginx html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config for SPA routing
RUN echo 'server { \
    listen 5176; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose frontend port
EXPOSE 5176

CMD ["nginx", "-g", "daemon off;"]
