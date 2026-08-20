ARG GIT_SHA=unknown
ARG BUILD_TIME=unknown

FROM node:22-alpine AS build

ARG GIT_SHA
ARG BUILD_TIME

WORKDIR /app

COPY package.json ./
RUN npm install

COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src

RUN npm run build

RUN printf '{\n  "service": "hap-frontend",\n  "git_commit": "%s",\n  "build_time": "%s",\n  "environment": "production"\n}\n' "$GIT_SHA" "$BUILD_TIME" > /app/dist/build-info.json

FROM nginx:1.27-alpine AS runtime

ARG GIT_SHA
ARG BUILD_TIME

LABEL org.opencontainers.image.source="https://github.com/sweet0416/home-analytics-platform" \
      org.opencontainers.image.revision="$GIT_SHA" \
      org.opencontainers.image.created="$BUILD_TIME"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
