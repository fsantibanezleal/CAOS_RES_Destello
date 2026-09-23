# deploy

The product is a static site: the built companion web plus the committed artifacts. Two targets, chosen by the
measured size of the export (design document, section 9):

- **GitHub Pages** at `destello.fasl-work.com`, when the export is under 900 MB in total and every file under 90 MB;
  see `pages.md`.
- **Static hosting on the ml box** at `destello.ml.fasl-work.com` otherwise, with the nginx site in `domain.nginx`.

The deploy never trains, simulates or rebuilds artifacts; it verifies the committed ones and publishes them.
