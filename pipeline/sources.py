"""Catálogo das fontes oficiais usadas no produto analítico de 2026."""
from dataclasses import dataclass


ROOT = "https://cdn.tse.jus.br/estatistica/sead/odsele"


@dataclass(frozen=True)
class Source:
    key: str
    path: str
    members: tuple[str, ...]
    required: tuple[str, ...]

    @property
    def url(self) -> str:
        return f"{ROOT}/{self.path}"

    @property
    def archive_name(self) -> str:
        return f"{self.key}.zip"


SOURCES = (
    Source("candidatos", "consulta_cand/consulta_cand_2026.zip",
           ("consulta_cand_2026_BRASIL.csv",), ("SQ_CANDIDATO", "SG_UF", "DS_CARGO")),
    Source("candidatos_complementar", "consulta_cand_complementar/consulta_cand_complementar_2026.zip",
           ("consulta_cand_complementar_2026_BRASIL.csv",), ("SQ_CANDIDATO", "NR_IDADE_DATA_POSSE")),
    Source("bens", "bem_candidato/bem_candidato_2026.zip",
           ("bem_candidato_2026_BRASIL.csv",), ("SQ_CANDIDATO", "VR_BEM_CANDIDATO")),
    Source("coligacoes", "consulta_coligacao/consulta_coligacao_2026.zip",
           ("consulta_coligacao_2026_BRASIL.csv",), ("SG_PARTIDO", "DS_CARGO")),
    Source("vagas", "consulta_vagas/consulta_vagas_2026.zip",
           ("consulta_vagas_2026_BRASIL.csv",), ("SG_UF", "DS_CARGO", "QT_VAGA")),
    Source("redes_sociais", "consulta_cand/rede_social_candidato_2026.zip",
           ("rede_social_candidato_2026_BRASIL.csv",), ("SQ_CANDIDATO", "DS_URL")),
    Source("motivo_cassacao", "motivo_cassacao/motivo_cassacao_2026.zip",
           ("motivo_cassacao_2026_BRASIL.csv",), ("SQ_CANDIDATO", "DS_MOTIVO")),
    Source("historico_candidatura", "historico_candidatura/historico_candidatura_2026.zip",
           ("historico_candidatura_2026_BRASIL.csv",), ("SQ_CANDIDATO_ATUAL", "ANO_ELEICAO")),
    Source("eleitorado", "perfil_eleitorado/perfil_eleitorado_2026.zip",
           ("perfil_eleitorado_2026_BRASIL.csv",), ("CD_MUNICIPIO", "QT_ELEITORES")),
    Source("eleitorado_deficiencia", "perfil_eleitor_deficiente/perfil_eleitor_deficiencia_2026.zip",
           ("perfil_eleitor_deficiencia_2026_BRASIL.csv",), ("SG_UF", "SQ_ELEITOR", "DS_TIPO_DEFICIENCIA")),
    Source("contas_partidarias", "prestacao_contas_anual_partidaria/prestacao_contas_anual_partidaria_2026.zip",
           ("receita_anual_2026_BRASIL.csv", "despesa_anual_2026_BRASIL.csv"),
           ("SG_PARTIDO",)),
    Source("contas_eleitorais", "prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2026.zip",
           ("receitas_candidatos_2026_BRASIL.csv", "receitas_candidatos_doador_originario_2026_BRASIL.csv",
            "despesas_contratadas_candidatos_2026_BRASIL.csv",
            "despesas_pagas_candidatos_2026_BRASIL.csv"),
           ("SG_UF",)),
    Source("contas_eleitorais_partidos", "prestacao_contas/prestacao_de_contas_eleitorais_orgaos_partidarios_2026.zip",
           ("receitas_orgaos_partidarios_2026_BRASIL.csv",
            "receitas_orgaos_partidarios_doador_originario_2026_BRASIL.csv",
            "despesas_contratadas_orgaos_partidarios_2026_BRASIL.csv",
            "despesas_pagas_orgaos_partidarios_2026_BRASIL.csv"),
           ("SG_UF",)),
    Source("pesquisas", "pesquisa_eleitoral/pesquisa_eleitoral_2026.zip",
           ("pesquisa_eleitoral_2026_BRASIL.csv",), ("SG_UF", "DS_CARGO", "QT_ENTREVISTADO")),
)

BY_KEY = {source.key: source for source in SOURCES}
