"""Configurazione S4 (spigoli centrati), parte sulla non interazione tra i condotti: legge input_S4.py.

    python run_S4.py            (oppure il tasto Run dell'editor)
    python run_S4.py --veloce   (griglia ridotta, per prove)
    python run_S4.py --input altro.py

Solo S4, quindi nessun grafico di confronto. Grafici di scenario: viste del layout, sezioni della struttura,
profili di velocità e pressione, perdite, indice di riaspirazione dei getti (ingestione). Excel completo.
Sintesi in risultati/<caso>/00_sintesi/RISULTATO.md.  La dinamica di volo di S4 è in ../Dinamica_Sistema_Propulsivo.
"""
import sys

from configurazioni_designer.cli import main

# Grafici di scenario prodotti da questa run (gli altri gruppi: ventola, spinta, dinamica, struttura)
GRUPPI = {"viste", "sezioni", "profili", "perdite", "ingestione"}

if __name__ == "__main__":
    sys.exit(main("S4", "input_S4.py", __doc__, gruppi=GRUPPI, con_confronto=False))
