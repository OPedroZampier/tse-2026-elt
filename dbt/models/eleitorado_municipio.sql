select
    SG_UF as uf,
    CD_MUNICIPIO as codigo_municipio,
    NM_MUNICIPIO as municipio,
    sum(try_cast(QT_ELEITORES as bigint)) as eleitores,
    sum(try_cast(QT_ELEITORES_BIOMETRIA as bigint)) as eleitores_biometria,
    sum(try_cast(QT_ELEITORES_DEFICIENCIA as bigint)) as eleitores_deficiencia,
    sum(try_cast(QT_ELEITORES_NOME_SOCIAL as bigint)) as eleitores_nome_social
from {{ source_csv('eleitorado', 'perfil_eleitorado_2026_BRASIL.csv') }}
group by 1, 2, 3
