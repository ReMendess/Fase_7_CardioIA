"""Backend central do CardioIA (Fase 7).

Pacote FastAPI que integra os modulos das Fases 3, 4, 5 e 6 sob um contrato unico.

Estado desta etapa: **Etapa C, itens 1 a 3** — esqueleto, envelope ``RespostaAPI[T]``,
enum de erros, ``GET /api/v1/health``, camada de persistencia (SQLAlchemy + SQLite) e
autenticacao (PyJWT + bcrypt + RBAC).

Documentacao de referencia:
- ``../CONTRATOS_API.md``
- ``../DECISOES_ARQUITETURAIS.md``
- ``../MODELO_DADOS.md``
- ``../PLANO_SEGURANCA.md``
"""

from __future__ import annotations

#: Nome do servico — usado em ``/health``, nos metadados do envelope e na auditoria.
NOME_DO_SERVICO = "cardioia-backend"

#: Versao do backend. Historico: 0.1.0 item 1 · 0.2.0 item 2 · 0.3.0 item 3.
__versao__ = "0.3.0"

__all__ = ["NOME_DO_SERVICO", "__versao__"]

