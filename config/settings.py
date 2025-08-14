senate = "senadores"
deputy = "diputados"

senate_url = f"https://sil.gobernacion.gob.mx/portal/ReporteSesion/{senate}"
deputy_url = f"https://sil.gobernacion.gob.mx/portal/ReporteSesion/{deputy}"

scrape_targets = [
        {"url": senate_url, "filename": "senadores.json"},
        {"url": deputy_url, "filename": "diputados.json"}]

outputTargets = [
        {"input_file": f"{senate}.json","output_file": f"{senate}_results.json", "url": senate_url},
        {"input_file": f"{deputy}.json", "output_file": f"{deputy}_results.json", "url": deputy_url},]