FROM node:18-alpine
WORKDIR /app

# 安装 sqlite3 编译依赖
RUN apk add --no-cache python3 make g++

# 复制依赖文件
COPY package*.json ./
RUN npm ci --only=production

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

EXPOSE 8001

CMD ["node", "server.js"]
