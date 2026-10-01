"""Execute: python -m streamlit run app.py"""
import io, json, copy, hashlib, zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from motor import calcular, EmpatePendente
from dados_tse import baixar, importar, carregar_cenario, PORTAL
from visual import CSS, CABECALHO, cartao_partido, icone_uri, rotulo

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Simulador Federal • SP 2026',page_icon='🗳️',layout='wide')
st.markdown(CSS,unsafe_allow_html=True)

def fmt(v): return f'{int(v):,}'.replace(',','.')
def assinatura(d): return hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def trocar(d):
    st.session_state.base=d
    st.session_state.revisao=st.session_state.get('revisao',0)+1
    st.session_state.pop('resultado',None)
    st.session_state.pop('assinatura_resultado',None)
    st.session_state['nome_cenario']=d['nome']

def csv(df): return df.drop(columns=['Ícone'],errors='ignore').to_csv(index=False,sep=';').encode('utf-8-sig')
def exibir_candidatos(rows):
    cols=['posicao','numero','nome','partido','grupo','votos','situacao_resultado','etapa','suplencia']
    df=pd.DataFrame(rows,columns=cols)
    df.insert(0,'Ícone', [icone_uri(p) for p in df['partido']])
    return df.rename(columns={'posicao':'Posição no grupo','numero':'Número','nome':'Candidato','partido':'Partido','grupo':'Partido / Federação','votos':'Votos','situacao_resultado':'Resultado','etapa':'Etapa da eleição','suplencia':'Ordem de suplência'})

def grafico(df,x,y,titulo,cor='#20649b'):
    fig,ax=plt.subplots(figsize=(10,max(3.8,.36*len(df))))
    ax.barh(df[x].astype(str),df[y],color=cor)
    ax.invert_yaxis(); ax.set_title(titulo,loc='left',weight='bold',pad=18)
    ax.set_xlabel(y); ax.spines[['top','right','left']].set_visible(False)
    ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True)
    for i,v in enumerate(df[y]): ax.annotate(fmt(v),(v,i),xytext=(5,0),textcoords='offset points',va='center',fontsize=9)
    ax.margins(x=.18); fig.tight_layout()
    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=180,bbox_inches='tight')
    st.pyplot(fig);plt.close(fig)
    return buf.getvalue()

if 'base' not in st.session_state:
    trocar(carregar_cenario((ROOT/'dados'/'candidatos_sp_2026.json').read_bytes()))
d=st.session_state.base
st.markdown(CABECALHO,unsafe_allow_html=True)
st.title('Simulador para cálculo de votações de deputados federais — Eleição 2026')
st.subheader('São Paulo • Eleições 2026 • 70 cadeiras')
st.write('Monte seus cenários de votos, acompanhe a força de cada partido e veja quem ocuparia as cadeiras da bancada paulista.')
st.caption('Preencha os votos por candidato e partido para comparar diferentes cenários eleitorais.')
st.info('Os nomes vêm da base do TSE. Os votos e os resultados são hipóteses preenchidas pelo participante. As federações são calculadas em conjunto.')

with st.sidebar:
    st.header('Seu cenário')
    d['nome']=st.text_input('Nome do cenário',key='nome_cenario',help='Dê um nome para identificar esta simulação. Exemplo: Cenário do Victor — reunião 1.')
    st.metric('Cadeiras em disputa',70,help='São Paulo elege 70 deputados federais. Este simulador é exclusivo para deputado federal/SP em 2026.')
    st.caption(f"Base do TSE: {d.get('meta',{}).get('geracao_tse','não informada')}")
    st.caption(f"{len(d['candidatos'])} registros • {len(d['legendas'])} partidos")
    st.download_button('💾 Baixar cenário',json.dumps(d,ensure_ascii=False,indent=2).encode(),'cenario_federal_sp.json','application/json',help='Salva candidatos, votos de legenda e votos individuais já aplicados. Antes, clique em Aplicar votos.')
    arq=st.file_uploader('Carregar cenário salvo',type=['json'],help='Selecione o JSON gerado em Baixar cenário. Ele substituirá o cenário exibido.')
    if st.button('Carregar cenário',disabled=arq is None):
        try: trocar(carregar_cenario(arq.getvalue()));st.rerun()
        except (ValueError,TypeError,KeyError) as e: st.error(str(e))
    with st.expander('Atualizar ou importar candidatos'):
        st.write('A atualização mantém votos por ID do candidato. Salve seu cenário antes de trocar a base.')
        if st.button('Buscar lista atual no TSE',help='Requer internet. Baixa os dados principais e tenta obter a situação dos registros no arquivo complementar.'):
            try:
                with st.spinner('Buscando candidatos no TSE…'): nova=baixar()
                antigos={c['id']:c for c in d['candidatos']}
                for c in nova['candidatos']:
                    if c['id'] in antigos: c['votos']=antigos[c['id']]['votos']
                nova['nome']=d['nome']
                nova['legendas']={p:d['legendas'].get(p,0) for p in nova['legendas']}
                trocar(nova);st.rerun()
            except Exception as e: st.error('Não foi possível atualizar. A base atual foi mantida. '+str(e))
        st.link_button('Abrir dados oficiais do TSE',PORTAL)
        principal=st.file_uploader('Consulta de candidatos — TSE',type=['zip','csv'],help='Arquivo consulta_cand_2026.zip ou consulta_cand_2026_SP.csv. O programa filtra SP e deputado federal.',key='principal')
        complementar=st.file_uploader('Consulta complementar — opcional',type=['zip','csv'],help='Arquivo consulta_cand_complementar_2026.zip ou consulta_cand_complementar_2026_SP.csv. Acrescenta a situação de julgamento.',key='complemento')
        if st.button('Importar arquivos TSE',disabled=principal is None):
            try:
                nova=importar(principal.getvalue(),complementar.getvalue() if complementar else None)
                nova['nome']=d['nome'];trocar(nova);st.rerun()
            except Exception as e: st.error(str(e))
    with st.expander('Limpar votação'):
        confirmar=st.checkbox('Quero zerar todos os votos',help='Zera votos individuais e de legenda, mantendo os candidatos. Salve seu cenário se desejar preservá-lo.')
        if st.button('Zerar votos',disabled=not confirmar):
            nova=copy.deepcopy(d)
            for c in nova['candidatos']: c['votos']=0
            nova['legendas']={p:0 for p in d['legendas']};trocar(nova);st.rerun()

t1,t2,t3,t4=st.tabs(['1 • Preencher votos','2 • Calcular e resultados','3 • Gráficos','? • Como usar'])
with t1:
    st.markdown('### Votos por candidato e partido')
    partido=st.selectbox('Partido para preencher',sorted(d['legendas']),format_func=rotulo,help='Escolha um partido. Os votos já aplicados aos outros partidos continuam guardados e participam do cálculo estadual.')
    candidatos=[c for c in d['candidatos'] if c['partido']==partido]
    grupos=sorted({c['grupo'] for c in candidatos})
    st.markdown(cartao_partido(partido,len(candidatos),', '.join(grupos)),unsafe_allow_html=True)
    st.write('Digite somente números inteiros na coluna **Votos**. Clique em **Aplicar votos deste partido** antes de trocar de partido, salvar ou calcular.')
    with st.form('votos_'+partido+'_'+str(st.session_state.revisao)):
        legenda=st.number_input('Votos de legenda deste partido',min_value=0,value=d['legendas'][partido],step=1000,help='Votos dados apenas ao número do partido. Não inclua novamente os votos dos candidatos: eles serão somados automaticamente.')
        dados=pd.DataFrame([{'Ícone':icone_uri(c['partido']),'ID':c['id'],'Número':c['numero'],'Candidato':c['nome'],'Partido / Federação':c['grupo'],'Situação no TSE':c.get('situacao_tse','Não informada'),'Considerar':c['considerar'],'Votos':c['votos'],'Nascimento':c.get('nascimento','')} for c in candidatos])
        editado=st.data_editor(dados,hide_index=True,width='stretch',height=530,
            disabled=['Ícone','ID','Número','Candidato','Partido / Federação','Situação no TSE'],
            column_config={
                'Ícone':st.column_config.ImageColumn('Partido',width='small',help='Identificador colorido com a sigla do partido. As imagens vêm no pacote e funcionam sem internet.'),
                'ID':None,
                'Votos':st.column_config.NumberColumn('Votos',min_value=0,step=1000,format='%d',required=True,help='Estimativa de votos válidos deste candidato em todo o estado. Zero significa que você ainda não atribuiu votos ou prevê zero.'),
                'Considerar':st.column_config.CheckboxColumn('Considerar',help='Marcado: votos entram no total e candidato pode disputar vagas. Desmarcado: votos e candidato são excluídos desta hipótese. Revise candidatos com recurso/renúncia e a situação do DRAP.',required=True),
                'Nascimento':st.column_config.TextColumn('Nascimento',help='Data no formato AAAA-MM-DD, usada para desempatar votos pela maior idade. A data oficial já vem preenchida quando disponível.'),
                'Candidato':st.column_config.TextColumn('Candidato',help='Nome de urna informado pelo TSE. Use a busca da tabela para localizar um nome (ícone de lupa).'),
                'Situação no TSE':st.column_config.TextColumn('Situação no TSE',help='Situação de julgamento na base importada. Não é previsão de resultado e pode mudar.'),
                'Partido / Federação':st.column_config.TextColumn('Partido / Federação',help='Partidos de uma mesma federação têm votos e classificação de candidatos calculados juntos.')},key='editor_'+partido+'_'+str(st.session_state.revisao))
        aplicar=st.form_submit_button('Aplicar votos deste partido',type='primary')
    if aplicar:
        try:
            nova=copy.deepcopy(d); mapa={str(r['ID']):r for r in editado.to_dict('records')}
            for c in nova['candidatos']:
                if c['id'] in mapa:
                    r=mapa[c['id']];c['votos']=int(r['Votos']);c['considerar']=bool(r['Considerar']);c['nascimento']=r['Nascimento'] or ''
            nova['legendas'][partido]=int(legenda)
            from motor import validar
            validar(nova['candidatos'],nova['legendas'])
            st.session_state.base=nova;d=nova;st.success('Votos aplicados. Pode trocar de partido ou calcular.');st.rerun()
        except (ValueError,TypeError) as e: st.error(str(e))
    validos=sum(c['votos'] for c in d['candidatos'] if c['considerar'])+sum(d['legendas'].values())
    a,b,c=st.columns(3)
    a.metric('Votos válidos no cenário',fmt(validos),help='Soma dos votos de candidatos marcados em Considerar e dos votos de legenda. Brancos, nulos e abstenções não entram.')
    b.metric('Partidos com votos',sum(1 for p in d['legendas'] if d['legendas'][p] or any(c['votos'] and c['considerar'] for c in d['candidatos'] if c['partido']==p)))
    c.metric('Candidatos com votos',sum(1 for c in d['candidatos'] if c['votos'] and c['considerar']))
    st.caption('O total estadual é calculado pelos votos preenchidos; não há um total externo acrescentado ao quociente.')
    with st.expander('Ver totais por partido e federação'):
        resumo=[]
        for p,l in d['legendas'].items():
            cs=[c for c in d['candidatos'] if c['partido']==p]
            v=sum(c['votos'] for c in cs if c['considerar'])
            resumo.append({'Partido':p,'Grupo':cs[0]['grupo'],'Votos individuais':v,'Votos de legenda':l,'Total':v+l,'Registros':len(cs)})
        st.dataframe(pd.DataFrame(resumo),hide_index=True,width='stretch')

with t2:
    st.markdown('### Distribuição das 70 cadeiras')
    st.caption('Preencha e aplique votos de todos os partidos que deseja representar. Partidos sem votos preenchidos contam como zero.')
    completo=st.checkbox('Revisei os votos estaduais e os candidatos considerados neste cenário',help='Confirme que o cenário representa a sua hipótese de votação estadual, inclusive os votos de legenda. Revise também federações e situação das candidaturas.')
    if st.button('Calcular eleitos e cadeiras',type='primary',disabled=not completo,help='Executa quociente partidário, sobras com limites de 80%/20% e sobras finais. Os gráficos aparecerão na aba 3.'):
        try:
            resultado=calcular(d['candidatos'],d['legendas'])
            st.session_state.resultado=resultado;st.session_state.assinatura_resultado=assinatura(d)
        except (ValueError,EmpatePendente) as e:
            st.session_state.pop('resultado',None);st.error(str(e))
    atual=st.session_state.get('assinatura_resultado')==assinatura(d)
    if 'resultado' in st.session_state and not atual:
        st.warning('O cenário mudou. Calcule novamente para atualizar os resultados e gráficos.')
    if 'resultado' in st.session_state and atual:
        r=st.session_state.resultado
        a,b,c,e=st.columns(4)
        a.metric('Votos válidos',fmt(r['total']),help='Somente votos individuais considerados e votos de legenda.')
        b.metric('Quociente eleitoral',fmt(r['qe']),help='Total de votos válidos / 70. Fração até 0,5 é desprezada; acima de 0,5 arredonda para cima.')
        c.metric('Cadeiras preenchidas',f"{r['preenchidas']} / 70",help='Se faltarem candidatos disponíveis, o cenário pode não preencher as 70 cadeiras.')
        e.metric('Mínimo individual — QP',fmt(r['min10']),help='Menor número inteiro de votos que alcança 10% do quociente eleitoral.')
        st.caption(f"Sobras: mínimo do grupo = {fmt(r['min80'])} votos (80% QE); mínimo do candidato = {fmt(r['min20'])} votos (20% QE). Sobras finais não exigem esses mínimos.")
        if r['preenchidas']<70: st.warning('Não há candidatos considerados suficientes para preencher todas as cadeiras desta hipótese.')
        st.markdown('#### Cadeiras por partido ou federação')
        resumo=pd.DataFrame(r['resumo']);st.dataframe(resumo,hide_index=True,width='stretch')
        st.markdown('#### Deputados eleitos neste cenário')
        eleitos=sorted([c for c in r['candidatos'] if c['eleito']],key=lambda c:-c['votos'])
        st.dataframe(exibir_candidatos(eleitos),hide_index=True,width='stretch',column_config={'Ícone':st.column_config.ImageColumn('Partido',width='small')})
        with st.expander('Ver todos os candidatos, suplência e filtros'):
            filtro=st.selectbox('Partido dos resultados',['Todos']+sorted(d['legendas']),format_func=lambda p: 'Todos os partidos' if p=='Todos' else rotulo(p),help='Este filtro muda apenas a exibição; o cálculo continua estadual.')
            busca=st.text_input('Buscar nome nos resultados',help='Digite parte do nome do candidato. Não altera os votos.')
            lista=[c for c in r['candidatos'] if (filtro=='Todos' or c['partido']==filtro) and busca.casefold() in c['nome'].casefold()]
            st.dataframe(exibir_candidatos(lista),hide_index=True,width='stretch',column_config={'Ícone':st.column_config.ImageColumn('Partido',width='small')})
            st.caption('Suplentes pertencem à lista conjunta da federação quando houver. Empates de suplentes com a mesma idade ficam sujeitos à definição oficial.')
        with st.expander('Conferir cada rodada de sobras'):
            if r['rodadas']: st.dataframe(pd.DataFrame(r['rodadas']),hide_index=True,width='stretch')
            else: st.write('Nenhuma cadeira distribuída por sobras neste cenário.')
            st.caption('Divisor da média = quociente partidário teórico + sobras já obtidas + 1, incluindo vagas de QP eventualmente não preenchidas.')
        st.markdown('#### Baixar resultados')
        a,b=st.columns(2)
        a.download_button('Baixar eleitos e suplentes (CSV)',csv(exibir_candidatos(r['candidatos'])),'resultado_candidatos.csv','text/csv')
        b.download_button('Baixar cadeiras por grupo (CSV)',csv(resumo),'resultado_cadeiras.csv','text/csv')
    elif 'resultado' not in st.session_state:
        st.write('Os resultados aparecerão após calcular.')

with t3:
    st.markdown('### Gráficos do cenário')
    if 'resultado' not in st.session_state or st.session_state.get('assinatura_resultado')!=assinatura(d):
        st.info('Calcule um cenário atualizado na aba 2 para gerar os gráficos.')
    else:
        r=st.session_state.resultado;grupos=pd.DataFrame(r['resumo'])
        imgs={}
        imgs['01_cadeiras_por_grupo.png']=grafico(grupos,'Grupo','Cadeiras','Cadeiras por partido ou federação')
        imgs['02_votos_por_grupo.png']=grafico(grupos.sort_values('Votos válidos',ascending=False),'Grupo','Votos válidos','Votos válidos por partido ou federação','#168575')
        partidos=[]
        for p in sorted(d['legendas']):
            cs=[c for c in r['candidatos'] if c['partido']==p]
            partidos.append({'Partido':p,'Cadeiras':sum(c['eleito'] for c in cs)})
        imgs['03_eleitos_por_partido.png']=grafico(pd.DataFrame(partidos).sort_values('Cadeiras',ascending=False),'Partido','Cadeiras','Eleitos por partido de filiação')
        st.caption('A distribuição de vagas é calculada pelo partido ou federação. Este gráfico por partido mostra a filiação dos candidatos eleitos na lista conjunta.')
        p=st.selectbox('Partido no gráfico de candidatos',sorted(d['legendas']),format_func=rotulo,help='Mostra os 20 candidatos mais votados deste partido no cenário. Eleitos da federação podem pertencer a outros partidos.')
        cs=sorted([c for c in r['candidatos'] if c['partido']==p and c['considerar']],key=lambda c:-c['votos'])[:20]
        if cs: imgs['04_candidatos_do_partido.png']=grafico(pd.DataFrame(cs).rename(columns={'nome':'Candidato','votos':'Votos'}),'Candidato','Votos',f'Votos simulados • {p} • até 20 candidatos','#bd8430')
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for nome,conteudo in imgs.items(): z.writestr(nome,conteudo)
        st.download_button('Baixar gráficos em PNG (ZIP)',buf.getvalue(),'graficos_federal_sp.zip','application/zip',help='Imagens em alta resolução dos gráficos exibidos nesta aba, para apresentações e compartilhamento.')

with t4:
    st.markdown('''### Como preencher
1. Na aba **Preencher votos**, escolha um partido.
2. Digite uma estimativa de votos em cada linha. Use números inteiros: **150000**, por exemplo.
3. Preencha os **votos de legenda**, sem repetir votos dos candidatos.
4. Revise a coluna **Considerar**. Candidatos desmarcados e seus votos ficam fora do cenário.
5. Clique em **Aplicar votos deste partido** e repita para os outros partidos.
6. Na aba **Calcular e resultados**, confirme a revisão e clique em **Calcular**.
7. Veja os gráficos na aba 3. Baixe o cenário para retomá-lo ou enviar a outra pessoa.

### Identificadores dos partidos
Cada partido tem um ícone colorido com sua sigla junto à listagem dos candidatos. São identificadores visuais do simulador, não logotipos oficiais. As federações continuam sendo calculadas em conjunto.

### Onde estão as ajudas “?”
Os campos têm ajudas ao lado do título. Na tabela, passe o mouse no cabeçalho da coluna para ler a orientação. As opções de importar, salvar, filtrar e calcular também têm explicações.

### Como o programa calcula
- **Votos válidos:** soma de votos individuais considerados e votos de legenda. Brancos, nulos e abstenções não entram.
- **Quociente eleitoral (QE):** votos válidos divididos por 70, com arredondamento eleitoral.
- **Quociente partidário (QP):** votos do partido ou federação divididos pelo QE, desprezando a fração.
- **Vagas iniciais:** candidatos mais votados do grupo com pelo menos 10% do QE, até o QP.
- **Sobras:** maiores médias entre grupos com 80% do QE e candidato disponível com 20% do QE.
- **Sobras finais:** maiores médias entre todos os grupos com candidatos disponíveis, sem aqueles mínimos.
- **Empate:** maior votação do grupo e depois votos do candidato na disputa da sobra; empate de votos dentro da lista usa maior idade. Empates sem solução pelos dados disponíveis interrompem o cálculo.

### Atenção ao cenário estadual
Preencher somente um partido cria uma hipótese em que os demais têm zero votos. Para uma comparação estadual, estime também os votos dos outros partidos. Os candidatos não preenchidos permanecem com zero.

### Situação das candidaturas
A base é uma fotografia do momento da importação. A marcação inicial considera registros deferidos, deferidos com recurso e aguardando julgamento. Outros registros vêm desmarcados; situações não informadas devem ser revistas. A decisão sobre “Considerar” é uma hipótese do participante. O programa não resolve decisões judiciais, cassações, substituições nem situação do DRAP. Desmarcar um candidato exclui também os seus votos; hipóteses de votos que passam só à legenda precisam ser lançadas em votos de legenda, sem duplicação.

### Salvar, compartilhar e comparar
Cada participante pode baixar seu JSON e abrir o próprio cenário. A versão 1 funciona localmente: compartilhar o ZIP não publica o aplicativo na internet. Para comparar cenários, carregue um por vez e exporte os resultados. O arquivo JSON contém os votos já aplicados; feche uma edição com “Aplicar votos” antes de baixar.
''')
    st.link_button('Norma consolidada do TSE', 'https://www.tse.jus.br/legislacao/compilada/res/2021/resolucao-no-23-677-de-16-de-dezembro-de-2021')
    st.link_button('Dados de candidatos — TSE',PORTAL)
    st.caption('Regras consultadas em 29/09/2026 • Resolução TSE 23.677/2021, alterada pela Resolução 23.748/2026. Resultado hipotético; não é apuração oficial.')
