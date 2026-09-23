# Deploy to GitHub Pages

Used when the measured export fits the Pages limits (under 900 MB in total, every file under 90 MB; design document,
section 9). The Pages workflow is added with the web base and does three things, in order:

1. **Verifies the committed artifacts** against the manifest (sizes and SHA-256), with the standard library only. It
   never simulates, trains, renders a case or rebuilds an artifact.
2. **Builds the web** (`cd frontend && npm ci && npm run build`); the build copies the committed artifacts into the
   site.
3. **Uploads and deploys** the built site.

One-time setup per repository: Settings, Pages, Source = GitHub Actions. The custom domain is set through the Pages
API, `gh api -X PUT repos/fsantibanezleal/CAOS_RES_Destello/pages -f cname=destello.fasl-work.com`, with a DNS
`CNAME destello -> fsantibanezleal.github.io`; a `CNAME` file alone does not bind the domain for an Actions deploy.
Deep links are served by copying `index.html` to `404.html` at build time.
