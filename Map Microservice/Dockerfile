# Node.js ve Expo için temel imajı kullan
FROM node:18-alpine

# Çalışma dizinini belirle
WORKDIR /app

# Bağımlılıkları önbelleğe almak için package.json ve package-lock.json dosyalarını kopyala
COPY package.json package-lock.json ./

# Bağımlılıkları yükle
RUN npm install -g expo-cli && npm install

# Proje dosyalarını kopyala
COPY . .

# Varsayılan port
EXPOSE 8081 19000 19001 19002

# Expo başlat
CMD ["npx", "expo", "start", "--tunnel"]
