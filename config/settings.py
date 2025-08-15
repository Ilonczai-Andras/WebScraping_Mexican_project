senate = "senadores"
deputy = "diputados"

senate_url = f"https://sil.gobernacion.gob.mx/portal/ReporteSesion/{senate}"
deputy_url = f"https://sil.gobernacion.gob.mx/portal/ReporteSesion/{deputy}"

scrape_targets = [
        {"url": senate_url, "filename": "senadores.json"},
        {"url": deputy_url, "filename": "diputados.json"}]