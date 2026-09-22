select
    SG_UF as uf,
    DS_CARGO as cargo,
    sum(try_cast(QT_VAGA as integer)) as vagas
from {{ source_csv('vagas', 'consulta_vagas_2026_BRASIL.csv') }}
where SG_UF not in ('#NULO', '#NE')
group by 1, 2
