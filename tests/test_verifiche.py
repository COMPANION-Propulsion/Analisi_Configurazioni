"""Le verifiche fisiche (configurazioni_designer/verifiche.py) come test pytest, una per una."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from configurazioni_designer import verifiche as VF          # noqa: E402

TEST = sorted(n for n in dir(VF) if n.startswith("test_"))


@pytest.mark.parametrize("nome", TEST)
def test_verifica(nome):
    VF.RISULTATI.clear()
    VF._STAMPA[0] = lambda *a, **k: None
    getattr(VF, nome)()
    falliti = [r for r in VF.RISULTATI if not r[1]]
    assert VF.RISULTATI and not falliti, falliti


def test_ponte_verso_la_dinamica():
    from configurazioni_designer.core.ponte_dinamica import propulsore
    percorso = propulsore.__file__.replace(os.sep, "/")
    assert percorso.endswith("Dinamica_Sistema_Propulsivo/dinamica_designer/propulsore.py")
