select
    SG_UF as uf,
    DS_CARGO as cargo,
    count(*) as pesquisas_registradas,
    sum(try_cast(QT_ENTREVISTADO as bigint)) as entrevistas_previstas
from {{ source_csv('pesquisas', 'pesquisa_eleitoral_2026_BRASIL.csv') }}
group by 1, 2
