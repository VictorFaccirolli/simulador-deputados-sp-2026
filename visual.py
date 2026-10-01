"""Identificadores visuais locais, com siglas. Não são logotipos oficiais."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parent
# Cor de identificação visual no simulador; não modifica dados eleitorais.
PARTIDOS={
 'AGIR':('AGIR','#126ab0','#e7b42c','Agir'),
 'AVANTE':('AVANTE','#de5f19','#163e66','Avante'),
 'CIDADANIA':('CIDADANIA','#ba225b','#5fbba8','Cidadania'),
 'DC':('DC','#174a8b','#e0b52c','Democracia Cristã'),
 'DEMOCRATA':('DEMOCRATA','#146849','#e0b52c','Democrata'),
 'MDB':('MDB','#14834a','#db443e','Movimento Democrático Brasileiro'),
 'MISSÃO':('MISSÃO','#243645','#e4b532','Missão'),
 'NOVO':('NOVO','#e56b19','#ffffff','Novo'),
 'PCDOB':('PCdoB','#bb202b','#edc52c','Partido Comunista do Brasil'),
 'PCO':('PCO','#b21f2c','#f3ca42','Partido da Causa Operária'),
 'PDT':('PDT','#b52b33','#ffffff','Partido Democrático Trabalhista'),
 'PL':('PL','#124487','#25a365','Partido Liberal'),
 'PODE':('PODE','#17759b','#6bc044','Podemos'),
 'PP':('PP','#17659b','#66b5d3','Progressistas'),
 'PRD':('PRD','#174481','#e9b430','Partido Renovação Democrática'),
 'PSB':('PSB','#b9212d','#efc332','Partido Socialista Brasileiro'),
 'PSD':('PSD','#1a773e','#edbb2f','Partido Social Democrático'),
 'PSDB':('PSDB','#1556a2','#ebc630','Partido da Social Democracia Brasileira'),
 'PSOL':('PSOL','#704386','#e9c630','Partido Socialismo e Liberdade'),
 'PSTU':('PSTU','#b71b2c','#e8c32a','Partido Socialista dos Trabalhadores Unificado'),
 'PT':('PT','#be202b','#ffffff','Partido dos Trabalhadores'),
 'PV':('PV','#167642','#a3cc44','Partido Verde'),
 'REDE':('REDE','#167d73','#e89931','Rede Sustentabilidade'),
 'REPUBLICANOS':('REP','#164b91','#efc434','Republicanos'),
 'SOLIDARIEDADE':('SOLIDARIEDADE','#b84d18','#174780','Solidariedade'),
 'UNIÃO':('UNIÃO','#165b9b','#edb629','União Brasil'),
 'UP':('UP','#ad2230','#e6bd2f','Unidade Popular'),
}

def info(partido): return PARTIDOS.get(partido,(partido,'#24556d','#6bc4bd',partido))

@lru_cache(maxsize=100)
def icone_uri(partido):
    nome=partido if partido in PARTIDOS else 'OUTROS'
    b=(ROOT/'assets'/'partidos'/f'{nome}.png').read_bytes()
    return 'data:image/png;base64,'+base64.b64encode(b).decode('ascii')

def rotulo(partido):
    # O seletor do Streamlit usa texto; o quadrado ajuda a reconhecer a cor.
    cores={'PL':'🟦','REPUBLICANOS':'🟦','PT':'🟥','PCDOB':'🟥','PCO':'🟥','PDT':'🟥','PSB':'🟥','PSTU':'🟥','UP':'🟥','MDB':'🟩','PV':'🟩','PSD':'🟩','DEMOCRATA':'🟩','PSOL':'🟪','NOVO':'🟧','AVANTE':'🟧','SOLIDARIEDADE':'🟧','CIDADANIA':'🟪'}
    return f"{cores.get(partido,'🟦')}  {partido}"

def cartao_partido(partido, quantidade, grupo):
    _,cor,acento,nome=info(partido)
    return f'''<div class="party-card" style="--party-color:{cor};--party-accent:{acento}">
<img class="party-icon" src="{icone_uri(partido)}" alt="Identificador {escape(partido)}">
<div><div class="party-name">{escape(nome)} <span class="party-sigla">{escape(partido)}</span></div>
<div class="party-detail">{quantidade} registros na lista · São Paulo</div>
<div class="party-group">Cálculo das cadeiras: {escape(grupo)}</div></div></div>'''

CABECALHO='''<div class="author-banner"><div class="author-eyebrow">SOFTWARE DESENVOLVIDO POR</div>
<div class="author-name">ENG. Victor Faccirolli</div><div class="author-detail">Simulação de votos e distribuição de cadeiras • Versão 1.1</div></div>'''
CSS='''<style>
.block-container{padding-top:2.5rem;max-width:1600px}
h1{color:#153e60;font-size:clamp(1.75rem,3.2vw,2.65rem)!important;line-height:1.18!important;max-width:1150px}
.stMetric{background:#eef5fb;border-radius:12px;padding:12px}
div[data-testid="stForm"]{border-radius:14px}footer{visibility:hidden}
.author-banner{background:linear-gradient(110deg,#102f49,#1c5470);border-left:5px solid #6bd0bd;border-radius:14px;padding:22px 26px;margin:0 0 24px;color:white;box-shadow:0 5px 20px #102f4910}
.author-eyebrow{font-family:Arial,sans-serif;font-size:11px;letter-spacing:2.2px;font-weight:700;color:#a9ded9;margin-bottom:5px}
.author-name{font-family:Georgia,'Times New Roman',serif;font-size:clamp(1.5rem,3vw,2.1rem);font-weight:700;line-height:1.3}
.author-detail{font-family:Arial,sans-serif;font-size:12px;color:#c7dbe5;margin-top:7px}
.party-card{display:flex;align-items:center;gap:18px;background:#f4f8fb;border:1px solid #e0e9ef;border-left:5px solid var(--party-color);border-radius:12px;padding:18px 20px;margin:12px 0 16px}
.party-icon{width:88px;height:64px;object-fit:contain;flex-shrink:0}
.party-name{font-size:20px;font-weight:700;color:#18354b;line-height:1.3}
.party-sigla{font-size:12px;display:inline-block;color:var(--party-color);border:1px solid #d5e1e8;background:white;padding:2px 7px;border-radius:6px;vertical-align:middle;margin-left:5px}
.party-detail{font-size:13px;color:#52697a;margin-top:5px}.party-group{font-size:12px;color:#52697a;margin-top:4px}
@media(max-width:640px){.author-banner{padding:18px}.party-card{gap:12px;padding:14px}.party-icon{width:64px;height:48px}.party-name{font-size:17px}}
</style>'''
