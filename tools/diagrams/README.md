# diagrams

Hand-drawn style SVG diagrams (Excalidraw look) rendered with [Rough.js](https://roughjs.com/).

```sh
cd tools/diagrams
npm ci
npm run diagrams   # specs/*.json -> docs/diagrams/*.svg
```

Each spec lists `groups`, `nodes` (`id`, `x`, `y`, `w`, `h`, `label`, `fill`, optional `shape: "ellipse"`), `edges` (`from`, `to`, optional `label`, `dashed`) and `notes`. Seeds are fixed, so output is deterministic: commit the regenerated SVGs together with the spec change.
