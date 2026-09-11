FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
RUN pnpm --filter web build

FROM node:22-alpine
WORKDIR /app
RUN corepack enable
COPY --from=build /app ./
CMD ["pnpm", "--filter", "web", "start"]
