# ICDC Data Generator MVP

This MVP focuses on one node at a time (starting with `sample`) and learns whether two properties are strongly related.

It does three things:
1. loads a flattened sample-node dataset,
2. computes pairwise relationship features,
3. ranks property pairs by relationship strength.
4. Required Noe4j as data source

# 📦 ICDC Data Generator MVP – Setup & Run Guide

## 🚀 Prerequisites

- Python **3.10+**
- uv (fast Python package manager)

Install uv:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

or via pip:

```bash
pip install uv
```

## 📁 Project Setup

```bash
git clone <your-repo-url>
cd icdc-data-generator-mvp
```

## ⚙️ Install Dependencies

```bash
uv sync
```

## ▶️ Run the Gradio App

```bash
uv run app
```

or:

```bash
uv run python -m icdc_data_generator_mvp.app
```

## 🧪 CLI Usage

```bash
uv run icdc-analyze \
  --study OSA01 \
  --nodes study,sample,case

uv run icdc-generate \
  --study OSA01 \
  --nodes study,sample,case
```

## 🔐 Environment Variables

```env
ICDC_NODE_MODEL_URL=...
ICDC_PROP_MODEL_URL=...
NEO4J_URI=...
NEO4J_USER=...
NEO4J_PASSWORD=...
```

## 🧠 uv Workflow

- uv add <package>
- uv sync
- uv run app.py

## ⚠️ Common Issues

- Run `uv sync` if modules missing
- Check env vars if nodes not loading
