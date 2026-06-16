name: Actualizar dashboard

on:
  schedule:
    - cron: "*/15 * * * *"      # cada 15 minutos
  workflow_dispatch:            # botón para ejecutar a mano
  push:
    branches: [ main ]

permissions:
  contents: write               # para commitear el store (la "BBDD") y data.json
  pages: write
  id-token: write

concurrency:
  group: dashboard
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -r requirements.txt

      - name: Recolectar y regenerar
        env:
          PIONEX_KEY: ${{ secrets.PIONEX_KEY }}
          PIONEX_SECRET: ${{ secrets.PIONEX_SECRET }}
        run: python collector/collect.py

      - name: Guardar cambios (store + data.json)
        run: |
          git config user.name  "dashboard-bot"
          git config user.email "bot@users.noreply.github.com"
          git add store site/data.json site/last_update.txt
          git commit -m "actualización automática" || echo "sin cambios"
          git push || echo "nada que empujar"

      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: update
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
