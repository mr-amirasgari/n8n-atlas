# n8n Atlas

A searchable directory of official and community n8n nodes.

n8n Atlas automatically collects node metadata from official n8n packages and community packages published on npm, then builds a static catalog that can be hosted directly on GitHub Pages.

## Features

- Official n8n nodes
- Community n8n nodes
- Real node display names extracted from package metadata
- Search
- Official / Community filters
- npm, GitHub, and website links
- Static frontend
- No backend required
- GitHub Pages ready

## Project Structure

```text
n8n-atlas/
├── data/
│   ├── nodes.json
│   ├── community-nodes.json
│   ├── community-enriched.json
│   └── catalog.json
│
├── scripts/
│   ├── collect_official.py
│   ├── collect_community.py
│   ├── enrich_community.py
│   └── build_catalog.py
│
├── index.html
├── style.css
├── app.js
├── .gitignore
└── .nojekyll
```

## Run Locally

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## Data Pipeline

```text
n8n official packages
        +
npm community packages
        ↓
collect
        ↓
enrich metadata
        ↓
build catalog
        ↓
catalog.json
        ↓
GitHub Pages
```

## Goal

The goal of n8n Atlas is to provide a clean and searchable directory for discovering n8n integrations and community nodes without requiring a backend or database server.