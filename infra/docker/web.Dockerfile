FROM node:22-alpine

WORKDIR /app

COPY apps/web/package.json /app/package.json
RUN npm install

COPY apps/web /app
RUN npm run build

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3100"]
