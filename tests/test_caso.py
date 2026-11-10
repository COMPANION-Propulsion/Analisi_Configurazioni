"""Run ridotta di S4 in una cartella temporanea: struttura del caso e rifiuto di input diversi."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from configurazioni_designer import cli                      # noqa: E402

RADICE = os.path.join(os.path.dirname(__file__), "..")
SOSTITUZIONI = [
    ('"verifiche_fisiche": True', '"verifiche_fisiche": False'),
    ('"diametri_mm": [26, 30, 34, 38, 42, 46, 50, 55, 60]', '"diametri_mm": [34]'),
    ('"lunghezza_frazione": [0.6, 0.7, 0.8, 0.9, 1.0]', '"lunghezza_frazione": [0.9]'),
    ('"spessore_parete_faccia_mm": [5.0, 10.0, 15.0]', '"spessore_parete_faccia_mm": [5.0]'),
    ('"spessore_attorno_condotto_mm": [3.0, 6.0, 10.0]', '"spessore_attorno_condotto_mm": [3.0]'),
]


def _input(tmp_path, nome, lato_max):
    t = open(os.path.join(RADICE, "input_S4.py"), encoding="utf-8").read()
    for a, b in SOSTITUZIONI + [('"cartella_output": "risultati"', f'"cartella_output": {str(tmp_path)!r}'),
                                ('"nome": None', f'"nome": {nome!r}'),
                                ('"lato_cubo_max_mm": 340.0', f'"lato_cubo_max_mm": {lato_max}')]:
        assert a in t, a
        t = t.replace(a, b)
    p = tmp_path / f"input_{nome}_{lato_max}.py"
    p.write_text(t, encoding="utf-8")
    return str(p)


@pytest.mark.slow
def test_run_scrive_il_caso(tmp_path):
    cart = cli.run(_input(tmp_path, None, 320.0), "S4", con_confronto=False)
    assert os.path.basename(cart).startswith("S4_F")
    for f in ("caso.json", "input_usato.py", "log.txt", "00_sintesi/RISULTATO.md", "00_sintesi/riepilogo.json",
              "02_excel/Confronto_scenari.xlsx", "03_dati/progetti.csv"):
        assert os.path.isfile(os.path.join(cart, f)), f
    assert os.listdir(os.path.join(cart, "01_grafici"))
    assert os.path.isfile(tmp_path / "registro_esecuzioni.csv")


@pytest.mark.slow
def test_caso_con_nome_rifiuta_input_diversi(tmp_path):
    cli.run(_input(tmp_path, "prova", 320.0), "S4", con_confronto=False)
    with pytest.raises(ValueError, match="altri input"):
        cli.run(_input(tmp_path, "prova", 340.0), "S4", con_confronto=False)
