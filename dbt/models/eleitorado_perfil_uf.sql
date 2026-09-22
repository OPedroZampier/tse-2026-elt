select
    SG_UF as uf,
    DS_GENERO as genero,
    DS_FAIXA_ETARIA as faixa_etaria,
    DS_GRAU_ESCOLARIDADE as escolaridade,
    DS_RACA_COR as raca_cor,
    sum(try_cast(QT_ELEITORES as bigint)) as eleitores
from {{ source_csv('eleitorado', 'perfil_eleitorado_2026_BRASIL.csv') }}
group by 1, 2, 3, 4, 5
