"""
Analisi delle configurazioni dei condotti di COMPANION: per ogni scenario cerca il progetto migliore
(lato del cubo, varianti geometriche, diametro, Venturi, ventola, motore).

    cli.py             sequenza della run (input_*.py -> risultati/<caso>/)
    ottimizzazione.py  ricerca dell'ottimo per scenario: lato x varianti x diametro
    valutazione.py     valutazione completa di un progetto (spazio, fluido, controllo, dinamica,
                       struttura, massa, realizzabilità, punteggi)
    verifiche.py       verifiche fisiche contro risultati noti (girano prima di ogni run)

    core/        config.py (lettura e controllo degli input), caso.py (cartella dei risultati),
                 ponte_dinamica.py (modello del propulsore da ../Dinamica_Sistema_Propulsivo)
    geometria/   geometria.py (voxel, distanze, spazio interno), scenari.py (generatori dei layout)
    fluido/      aria.py, perdite.py (correlazioni), rete.py (rete 1D), ventole.py, costruttore.py
    modelli/     prestazioni.py (forze, momenti, guasti, ingestione), struttura.py, massa.py,
                 realizzabilita.py
    export/      grafici.py, report_excel.py, sintesi.py (RISULTATO.md, riepilogo.json, progetti.csv)
"""
