# data

| Folder | Tracked | Content |
|---|---|---|
| `raw/` | no | release files and other sources, fetched and hash-checked by the ingest stage (the heavy copies live in the data vault outside the repository) |
| `examples/` | yes | tiny samples that pass the ingestion contract, for tests |
| `derived/` | yes | the compact artifacts the web replays, each listed in the manifest with its size and SHA-256 |

The ingestion contract (what the pipeline accepts and how it rejects what it cannot use) and the artifact contract
(what the web may read) are specified in the design document, `docs/design/SDD.md`, section 4, and documented in
detail in the wiki as the stages that enforce them land.

Sources and licences: MaleCNS v1.0, Berg et al., *Cell* 189:5504-5526 (2026), doi:10.1016/j.cell.2026.08.015,
CC BY 4.0, from `https://male-cns.janelia.org/download/`.
