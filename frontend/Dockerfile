### Stage 1: build
FROM node:18-alpine AS build
WORKDIR /app

# Install deps
COPY besscom/frontend/package*.json ./
RUN npm ci --silent

# Copy source and build
COPY besscom/frontend/ ./
RUN npm run build

### Stage 2: serve with nginx
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Optional: keep default nginx config; users can add custom config at frontend/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
