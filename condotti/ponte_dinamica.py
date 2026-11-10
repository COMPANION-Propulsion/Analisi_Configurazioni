"""Collegamento ai modelli di dinamica, che stanno nella cartella sorella Dinamica_Sistema_Propulsivo.

L'analisi usa il modello del propulsore (salita della spinta, inversione, margine di fase, ruote di
reazione) di Dinamica_Sistema_Propulsivo/dinamica/propulsore.py: il codice esiste in una sola copia.

Struttura attesa (le due cartelle una accanto all'altra):
    Companion-Propulsion/
        Analisi_Configurazioni/        (questa)
        Dinamica_Sistema_Propulsivo/
            dinamica/propulsore.py
"""
import os
import sys

CARTELLA_DINAMICA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                 "Dinamica_Sistema_Propulsivo")

if not os.path.isfile(os.path.join(CARTELLA_DINAMICA, "dinamica", "propulsore.py")):
    raise ImportError(f"Modello di dinamica non trovato in {CARTELLA_DINAMICA}: la cartella "
                      "Dinamica_Sistema_Propulsivo deve stare accanto ad Analisi_Configurazioni.")
if CARTELLA_DINAMICA not in sys.path:
    sys.path.append(CARTELLA_DINAMICA)

from dinamica import propulsore                                      # noqa: E402,F401
