"""Collegamento ai modelli di dinamica, che stanno nella cartella sorella Dinamica_Sistema_Propulsivo.

L'analisi usa il modello del propulsore (salita della spinta, inversione, margine di fase, ruote di
reazione) di Dinamica_Sistema_Propulsivo/dinamica_designer/propulsore.py: il codice esiste in una sola copia.

Struttura attesa (le due cartelle una accanto all'altra):
    Companion-Propulsion/
        Analisi_Configurazioni/        (questa)
        Dinamica_Sistema_Propulsivo/
            dinamica_designer/propulsore.py
"""
import os
import sys

_QUI = os.path.dirname(os.path.abspath(__file__))                         # .../configurazioni_designer/core
CARTELLA_DINAMICA = os.path.normpath(os.path.join(_QUI, "..", "..", "..", "Dinamica_Sistema_Propulsivo"))

if not os.path.isfile(os.path.join(CARTELLA_DINAMICA, "dinamica_designer", "propulsore.py")):
    raise ImportError(f"Modello di dinamica non trovato in {CARTELLA_DINAMICA}: la cartella "
                      "Dinamica_Sistema_Propulsivo deve stare accanto ad Analisi_Configurazioni.")
if CARTELLA_DINAMICA not in sys.path:
    sys.path.append(CARTELLA_DINAMICA)

from dinamica_designer import propulsore                             # noqa: E402,F401
