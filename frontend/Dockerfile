# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 生产阶段 - Nginx 静态服务
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 配置：所有路由回退到 index.html（SPA），/api 反向代理到后端
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
