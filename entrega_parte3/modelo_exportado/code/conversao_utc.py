"""
Conversão de UTC para horário de Brasília (contrato v1.1, turma A).

Desde a semana 14 (migração para a Vértice) hora_transacao e dia_semana
chegam em UTC. O modelo foi treinado em horário de Brasília (UTC-3), então
esta etapa converte antes do pré-processamento. Ela não aprende nada no fit.
"""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class HoraUTCParaBrasilia(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        h = X["hora_transacao"].astype(int) - 3
        X["dia_semana"] = np.where(h < 0, (X["dia_semana"].astype(int) - 1) % 7, X["dia_semana"].astype(int))
        X["hora_transacao"] = h % 24
        return X

    def __sklearn_is_fitted__(self):
        return True
