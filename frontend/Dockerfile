# Two-stage build: compile the React app, then serve the static bundle
# with nginx. nginx also proxies /api/* to the FastAPI backend so the
# browser only ever talks to one origin in production.
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build


FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
