select
    SG_UF as uf,
    CD_MUNICIPIO as codigo_municipio,
    NM_MUNICIPIO as municipio,
    DS_TIPO_DEFICIENCIA as tipo_deficiencia,
    count(distinct SQ_ELEITOR) as eleitores
from {{ source_csv('eleitorado_deficiencia', 'perfil_eleitor_deficiencia_2026_BRASIL.csv') }}
group by 1, 2, 3, 4
