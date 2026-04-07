FROM alpine:latest
WORKDIR /app

# 安装 nodejs 和 npm
RUN apk add --no-cache nodejs npm

# 复制依赖文件
COPY package*.json ./

# 安装 express 和 uuid（sqlite3 会在 npm install 时自动处理）
RUN npm install express sqlite3 uuid

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

EXPOSE 8001

CMD ["node", "server.js"]
