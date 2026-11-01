"""Constantes de paginacao compartilhadas pelas listagens da API.

Um unico lugar para o teto e o padrao: se cada rota definisse os seus, a API ficaria
inconsistente (uma listagem aceitaria 200 itens, outra 50) e o cliente nao teria como
prever o comportamento.
"""

from __future__ import annotations

__all__ = ["LIMITE_MAXIMO_DE_PAGINA", "LIMITE_PADRAO_DE_PAGINA"]

#: Teto de itens por pagina — protege o servidor de uma listagem sem limite.
LIMITE_MAXIMO_DE_PAGINA = 200

#: Quantidade de itens devolvida quando o cliente nao informa ``limite``.
LIMITE_PADRAO_DE_PAGINA = 50
