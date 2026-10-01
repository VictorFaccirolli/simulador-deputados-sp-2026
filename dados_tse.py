"""Importa dados públicos do TSE, retendo só campos úteis à simulação."""
import io, json, zipfile
from datetime import datetime
import pandas as pd

URL_BASE='https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip'
URL_COMPLEMENTAR='https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand_complementar/consulta_cand_complementar_2026.zip'
PORTAL='https://dadosabertos.tse.jus.br/dataset/candidatos-2026'

def texto(v):
    s=str(v).strip()
    return '' if s in ['','nan','#NULO','#NE','-1','-3'] else s

def ler_csv_zip(conteudo, complementar=False):
    if conteudo[:2]==b'PK':
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            alvo='consulta_cand_complementar_2026_SP.csv' if complementar else 'consulta_cand_2026_SP.csv'
            nomes=[n for n in z.namelist() if n.split('/')[-1]==alvo]
            if not nomes: raise ValueError(f'O ZIP não contém {alvo}.')
            info=z.getinfo(nomes[0])
            if info.file_size>200_000_000: raise ValueError('Arquivo CSV grande demais.')
            conteudo=z.read(nomes[0])
    try: s=conteudo.decode('utf-8-sig')
    except UnicodeDecodeError: s=conteudo.decode('latin1')
    return pd.read_csv(io.StringIO(s),sep=';',dtype=str,keep_default_na=False)

def importar(base, complemento=None):
    df=ler_csv_zip(base)
    obrig=['SG_UF','CD_CARGO','SQ_CANDIDATO','NM_URNA_CANDIDATO','NR_CANDIDATO','SG_PARTIDO','ANO_ELEICAO','NR_TURNO']
    if not set(obrig)<=set(df.columns): raise ValueError('Arquivo não é a consulta de candidatos do TSE esperada.')
    df=df[(df.SG_UF=='SP') & (df.CD_CARGO=='6') & (df.ANO_ELEICAO=='2026') & (df.NR_TURNO=='1')].copy()
    if df.empty: raise ValueError('Nenhum deputado federal de SP/2026 no arquivo.')
    if df.SQ_CANDIDATO.duplicated().any(): raise ValueError('Há candidaturas duplicadas no arquivo de origem.')
    comp={}
    if complemento:
        d=ler_csv_zip(complemento,True)
        if 'SQ_CANDIDATO' not in d: raise ValueError('Complemento inválido.')
        if 'ANO_ELEICAO' in d: d=d[d.ANO_ELEICAO=='2026']
        comp={r['SQ_CANDIDATO']:r for r in d.to_dict('records')}
    candidatos=[]
    for r in df.to_dict('records'):
        cr=comp.get(r['SQ_CANDIDATO'],{})
        status=next((texto(cr.get(k,'')) for k in ['DS_SITUACAO_JULGAMENTO','DS_SITUACAO_CANDIDATO_TOT','DS_DETALHE_SITUACAO_CAND'] if texto(cr.get(k,''))),texto(r.get('DS_SITUACAO_CANDIDATURA','')))
        status=status or 'Não informada'
        fed=texto(r.get('NM_FEDERACAO','')) if texto(r.get('NR_FEDERACAO','')) else ''
        dt=pd.to_datetime(texto(r.get('DT_NASCIMENTO','')),format='%d/%m/%Y',errors='coerce')
        considerar=status.upper().startswith('DEFERIDO') or status.upper() in ['AGUARDANDO JULGAMENTO','PENDENTE DE JULGAMENTO','NÃO INFORMADA']
        # Não presumir votos válidos para registros indeferidos/renunciados.
        candidatos.append({'id':r['SQ_CANDIDATO'],'numero':r['NR_CANDIDATO'],'nome':r['NM_URNA_CANDIDATO'],'partido':r['SG_PARTIDO'],'grupo':fed or r['SG_PARTIDO'],'nascimento':dt.strftime('%Y-%m-%d') if pd.notna(dt) else '', 'situacao_tse':status,'considerar':considerar,'votos':0})
    return {'versao':1,'nome':'Meu cenário','candidatos':candidatos,'legendas':{p:0 for p in sorted(df.SG_PARTIDO.unique())},'meta':{'fonte':PORTAL,'geracao_tse':df.iloc[0].get('DT_GERACAO','')+' '+df.iloc[0].get('HH_GERACAO',''),'importacao':datetime.now().isoformat(timespec='seconds'),'complemento':bool(complemento),'tipo':'Base oficial TSE; votos simulados'}}

def baixar():
    import requests
    def get(url):
        r=requests.get(url,timeout=(15,90)); r.raise_for_status()
        if len(r.content)>100_000_000: raise ValueError('Download muito grande.')
        return r.content
    base=get(URL_BASE)
    try:
        return importar(base,get(URL_COMPLEMENTAR))
    except requests.RequestException:
        return importar(base)

def carregar_cenario(conteudo):
    from motor import validar
    d=json.loads(conteudo)
    if not isinstance(d,dict) or d.get('versao')!=1: raise ValueError('Formato de cenário inválido.')
    c,l=validar(d.get('candidatos',[]),d.get('legendas',{}))
    d['candidatos']=c; d['legendas']=l
    d['nome']=str(d.get('nome','Cenário importado'))[:150]
    if not isinstance(d.get('meta',{}),dict): raise ValueError('Metadados inválidos.')
    return d
