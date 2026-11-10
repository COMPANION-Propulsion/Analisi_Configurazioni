"""Confronto tra le configurazioni S1, S2 e S3: legge input_generico.py, scrive risultati/<caso>/.

    python run_generica.py            (oppure il tasto Run dell'editor)
    python run_generica.py --veloce   (griglia ridotta, per prove)
    python run_generica.py --input altro.py

Fa verifiche fisiche, ottimizzazione di ogni scenario, grafici di scenario e di confronto, Excel.
Sintesi in risultati/<caso>/00_sintesi/RISULTATO.md.
"""
import sys

from configurazioni_designer.cli import main

if __name__ == "__main__":
    sys.exit(main("generica", "input_generico.py", __doc__))
