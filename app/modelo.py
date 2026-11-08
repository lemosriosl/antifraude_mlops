"""
O modelo em produção é SEMPRE o models:/<NOME_MODELO>@champion do MLflow.

Trocar o modelo em produção = mover o alias champion (no MLflow, pelo seu
notebook). O sistema percebe sozinho na próxima chamada e anota a troca na
tabela trocas_modelo, com o motivo que estiver na tag `motivo` da versão.

O que o sistema espera da versão registrada
-------------------------------------------
1. Recebe um DataFrame com as 13 features do contrato, CRUAS, na ordem do
   contrato. Todo pré-processamento mora dentro do modelo (Pipeline).
2. Tem predict_proba (sabor sklearn do MLflow). Se o modelo foi registrado
   como pyfunc, o predict precisa devolver a probabilidade de fraude.
3. Tem a tag `threshold` NA VERSÃO (não na run), com o corte de bloqueio.
   score >= threshold -> bloqueia.
"""
import threading

import mlflow
import numpy as np
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

import config
from app import banco, contrato


class SemModeloEmProducao(Exception):
    pass


class _Producao:
    def __init__(self):
        self._lock = threading.Lock()
        self.versao = None
        self.threshold = None
        self.run_id = None
        self.descricao = None
        self._modelo = None
        self._sklearn = False

    def _cliente(self):
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        return MlflowClient()

    def atualizar(self):
        """Confere no MLflow quem é o champion agora; recarrega se mudou."""
        try:
            mv = self._cliente().get_model_version_by_alias(config.NOME_MODELO, config.ALIAS_PRODUCAO)
        except MlflowException as e:
            raise SemModeloEmProducao(
                f"Não há '{config.NOME_MODELO}@{config.ALIAS_PRODUCAO}' no MLflow ({config.MLFLOW_TRACKING_URI}). "
                "Registre um modelo e aponte o alias champion para ele.") from e
        if mv.version == self.versao:
            return self
        if config.TAG_THRESHOLD not in mv.tags:
            raise SemModeloEmProducao(
                f"A versão {mv.version} não tem a tag '{config.TAG_THRESHOLD}'. "
                "Grave o threshold como tag da VERSÃO do modelo (client.set_model_version_tag).")
        with self._lock:
            uri = f"models:/{config.NOME_MODELO}/{mv.version}"
            try:
                self._modelo = mlflow.sklearn.load_model(uri)
                self._sklearn = hasattr(self._modelo, "predict_proba")
            except Exception:
                self._modelo = mlflow.pyfunc.load_model(uri)
                self._sklearn = False
            anterior = banco.ultima_troca()
            self.versao = mv.version
            self.threshold = float(mv.tags[config.TAG_THRESHOLD])
            self.run_id = mv.run_id
            self.descricao = mv.description
            if anterior is None or str(anterior["versao_nova"]) != str(mv.version):
                banco.registrar_troca(None if anterior is None else anterior["versao_nova"],
                                      mv.version, self.threshold, mv.tags.get(config.TAG_MOTIVO))
        return self

    def pontuar(self, df):
        """df com as features do contrato -> array de scores (prob. de fraude)."""
        self.atualizar()
        X = contrato.tipar(df[contrato.nomes_features()])
        if self._sklearn:
            return self._modelo.predict_proba(X)[:, 1]
        saida = np.asarray(self._modelo.predict(X), dtype=float)
        return saida[:, -1] if saida.ndim == 2 else saida


producao = _Producao()
