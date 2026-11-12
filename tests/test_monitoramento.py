import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import features
import monitorar_semana
from monitoramento import colunas_monitoradas, drift_continuas, performance, saida_modelo


class MonitoramentoTest(unittest.TestCase):
    def setUp(self):
        self.referencia = pd.DataFrame({
            "canal": ["pix", "pix", "cartao_online"],
            "fraude": [1, 0, 0],
            "score": [0.20, 0.30, 0.10],
            "valor_transacao": [400, 100, 200],
        })

    def test_contrato_independe_da_pasta_do_modulo_features(self):
        copia_mlflow = Path("artefato_sem_contrato") / "features.py"
        with (
            patch.object(features, "__file__", str(copia_mlflow)),
            patch.object(features, "_CAMINHO_CONTRATO", copia_mlflow.parent / "contrato_features.yaml"),
        ):
            continuas, discretas = colunas_monitoradas()
        self.assertIn("score", continuas)
        self.assertIn("canal", discretas)
        self.assertEqual(len(continuas) + len(discretas), 14)

    def test_segmento_novo_tem_metricas_sem_comparacao(self):
        lote = self.referencia.assign(canal="cartao_presencial")
        tabela = performance(self.referencia, lote, 0.29)
        canal = tabela.query("conjunto == 'lote' and segmento == 'canal'").iloc[0]
        self.assertEqual(canal["status_comparacao"], "segmento_sem_referencia")
        self.assertEqual(canal["custo"], 415.0)
        self.assertFalse(canal["alerta"])

    def test_rotulo_parcial_nao_entra_no_custo_observado(self):
        lote = self.referencia.copy()
        lote["fraude"] = [1, np.nan, 0]
        tabela = performance(self.referencia, lote, 0.29)
        global_lote = tabela.query("conjunto == 'lote' and segmento == 'global'").iloc[0]
        self.assertAlmostEqual(global_lote["cobertura_rotulos"], 2 / 3)
        self.assertEqual(global_lote["custo_observado"], 400.0)
        self.assertTrue(pd.isna(global_lote["custo"]))
        self.assertTrue(pd.isna(global_lote["custo_por_mil"]))
        self.assertFalse(global_lote["alerta"])
        self.assertEqual(global_lote["status_comparacao"], "rotulos_pendentes")

    def test_rotulos_completos_preservam_custo_e_alerta(self):
        lote = self.referencia.assign(valor_transacao=[1000, 100, 200])
        tabela = performance(self.referencia, lote, 0.29)
        global_lote = tabela.query("conjunto == 'lote' and segmento == 'global'").iloc[0]
        self.assertEqual(global_lote["cobertura_rotulos"], 1)
        self.assertEqual(global_lote["custo"], 1015.0)
        self.assertEqual(global_lote["status_comparacao"], "comparado")
        self.assertIn("aumento_custo_por_mil", global_lote["motivos_alerta"])

    def test_ks_sem_amostra_valida(self):
        lote = pd.DataFrame({"x": [np.nan, np.inf, -np.inf]})
        tabela = drift_continuas(pd.DataFrame({"x": [0.0, 1.0]}), lote, ["x"])
        self.assertEqual(tabela.loc[0, "invalidos_lote"], 3)
        self.assertEqual(tabela.loc[0, "status"], "sem_amostra_valida")
        self.assertTrue(pd.isna(tabela.loc[0, "D"]))
        self.assertFalse(tabela.loc[0, "alerta"])

    def test_saida_rejeita_score_fora_do_intervalo(self):
        lote = self.referencia.assign(score=[0.20, np.inf, 0.10])
        with self.assertRaisesRegex(ValueError, "score"):
            saida_modelo(self.referencia, lote, 0.29)

    def test_comando_rejeita_lote_pontuado_com_outro_corte(self):
        lote = self.referencia.assign(versao_modelo="3", threshold=[0.29, 0.5, 0.29])
        with (
            patch("sys.argv", ["monitorar_semana.py", "13"]),
            patch.object(monitorar_semana, "carregar_referencia_champion",
                         return_value=(self.referencia, 0.29, "3")),
            patch.object(monitorar_semana, "carregar_semana", return_value=lote),
            self.assertRaisesRegex(ValueError, "outro threshold"),
        ):
            monitorar_semana.main()


if __name__ == "__main__":
    unittest.main()
