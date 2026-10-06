select uf, cargo, codigo_cargo, partido, resultado as forma_eleicao,
       turno, ano_eleicao, count(*)::bigint as quantidade
from {{ ref('votos_candidatos_primeiro_turno') }}
where codigo_cargo in (6, 7, 8) and resultado in ('Eleito por QP', 'Eleito por média')
group by uf, cargo, codigo_cargo, partido, resultado, turno, ano_eleicao
