# ===== 前端镜像：Node 打包 → nginx 托管 =====

# ---------- 阶段一：构建静态文件 ----------
FROM node:20-alpine AS builder

WORKDIR /app

# 使用国内 npm 镜像，加速依赖下载
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

# 先拷依赖清单，利用层缓存
COPY package.json package-lock.json ./
RUN npm ci

# 拷贝源码并打包
COPY . .
RUN npm run build

# ---------- 阶段二：nginx 托管 ----------
FROM nginx:1.27-alpine

# 用自定义 nginx 配置（静态托管 + /api 反向代理）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 把打包产物放进 nginx 静态目录
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
