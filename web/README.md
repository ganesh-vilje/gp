# web

Node **22.21.0** (see `.nvmrc`) — the exact build-machine version, not just the `22.x` LTS line.
`jsdom` is pinned to `27.2.0` (not the newer `30.x`) because `30.x` requires Node `^22.22.2`, which
this machine does not have; `27.x` only requires `^22.12.0`.

Gate commands (run from `web/`):

```
npm ci --ignore-scripts
npm run build
npx biome ci .
npx tsc --noEmit
npm run test
```
