with source as (
    select * from {{ source_csv('candidatos', 'consulta_cand_2026_BRASIL.csv') }}
),
typed as (
    select
        try_cast(ANO_ELEICAO as integer) as ano_eleicao,
        try_cast(SQ_CANDIDATO as bigint) as id_candidato,
        nullif(trim(NM_URNA_CANDIDATO), '#NULO') as nome_urna,
        nullif(trim(NM_CANDIDATO), '#NULO') as nome_candidato,
        nullif(trim(SG_UF), '#NULO') as uf,
        nullif(trim(DS_CARGO), '#NULO') as cargo,
        nullif(trim(SG_PARTIDO), '#NULO') as partido,
        nullif(trim(DS_GENERO), '#NULO') as genero,
        nullif(trim(DS_COR_RACA), '#NULO') as raca_cor,
        nullif(trim(DS_GRAU_INSTRUCAO), '#NULO') as escolaridade,
        nullif(trim(DS_OCUPACAO), '#NULO') as ocupacao,
        nullif(trim(DS_SITUACAO_CANDIDATURA), '#NULO') as situacao_candidatura,
        try_strptime(DT_NASCIMENTO, '%d/%m/%Y')::date as data_nascimento,
        try_strptime(DT_GERACAO, '%d/%m/%Y')::date as data_extracao,
        row_number() over (
            partition by SQ_CANDIDATO
            order by try_strptime(DT_GERACAO, '%d/%m/%Y') desc nulls last,
                     try_strptime(HH_GERACAO, '%H:%M:%S') desc nulls last
        ) as ordem
    from source
)
select * exclude (ordem)
from typed
where ordem = 1 and id_candidato is not null and ano_eleicao = 2026
