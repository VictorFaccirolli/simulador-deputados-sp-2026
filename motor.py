"""Distribuição proporcional: Res. TSE 23.677/2021, arts. 8 a 14 (2026).
Médias usam QP teórico + sobras obtidas, mesmo se vagas de QP não preenchidas.
Empates sem critério suficiente interrompem a simulação, sem sorteio implícito.
"""
from fractions import Fraction
from datetime import date
from collections import defaultdict

CADEIRAS = 70

class EmpatePendente(ValueError):
    pass

def inteiro(valor, campo):
    if isinstance(valor, bool):
        raise ValueError(f'{campo}: informe um número inteiro, não uma opção sim/não.')
    try:
        v = int(valor)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'{campo}: informe um inteiro não negativo.') from None
    if v < 0 or str(v) != str(valor).strip():
        raise ValueError(f'{campo}: informe um inteiro não negativo, sem separadores.')
    return v

def validar(candidatos, legendas):
    if not candidatos:
        raise ValueError('Cadastre ou importe os candidatos primeiro.')
    ids = set(); partidos = {}; limpos = []
    for c in candidatos:
        c = dict(c)
        for k in ['id','nome','numero','partido','grupo']:
            if not isinstance(c.get(k), str) or not c[k].strip():
                raise ValueError(f'Campo {k} ausente no cadastro de candidato.')
        if c['id'] in ids:
            raise ValueError('Há IDs de candidatos duplicados na base.')
        ids.add(c['id'])
        if c['partido'] in partidos and partidos[c['partido']] != c['grupo']:
            raise ValueError(f"O partido {c['partido']} está associado a grupos diferentes.")
        partidos[c['partido']] = c['grupo']
        c['votos'] = inteiro(c.get('votos',0), c['nome'])
        if not isinstance(c.get('considerar'), bool):
            raise ValueError('O campo considerar deve ser verdadeiro ou falso.')
        nascimento = c.get('nascimento','')
        if nascimento:
            try: date.fromisoformat(nascimento)
            except (TypeError,ValueError): raise ValueError(f"Data de nascimento inválida: {c['nome']}") from None
        limpos.append(c)
    if set(legendas)-set(partidos):
        raise ValueError('Votos de legenda informados para partido ausente na base.')
    return limpos, {p:inteiro(legendas.get(p,0),f'Legenda {p}') for p in partidos}

def chave_candidato(c):
    return (-c['votos'], c.get('nascimento') or '9999-12-31', c['id'])

def verificar_escolha(c, lista):
    # A ordenação técnica por ID não pode decidir uma cadeira empatada.
    empatados = [x for x in lista if x['votos']==c['votos']]
    if len(empatados)>1:
        if any(not x.get('nascimento') for x in empatados):
            raise EmpatePendente('Empate de votos: preencha a data de nascimento de '+', '.join(x['nome'] for x in empatados))
        mesma_idade = [x for x in empatados if x['nascimento']==c['nascimento']]
        if len(mesma_idade)>1:
            raise EmpatePendente('Empate de votos e idade sem solução automática: '+', '.join(x['nome'] for x in mesma_idade))

def calcular(candidatos, legendas, cadeiras=CADEIRAS):
    candidatos, legendas = validar(candidatos,legendas)
    cadeiras = inteiro(cadeiras,'Cadeiras')
    if cadeiras<1: raise ValueError('Número de cadeiras inválido.')
    grupos = {}; listas = defaultdict(list); totais = defaultdict(int)
    for c in candidatos:
        grupos[c['partido']] = c['grupo']
        if c['considerar']:
            listas[c['grupo']].append(c)
            totais[c['grupo']] += c['votos']
    for p,g in grupos.items(): totais[g] += legendas[p]
    total = sum(totais.values())
    if total==0: raise ValueError('Preencha os votos antes de calcular.')
    q,r = divmod(total,cadeiras)
    qe = q + (2*r>cadeiras) # fração exatamente 0,5 é desprezada
    if qe<1: raise ValueError('Votos insuficientes para obter quociente eleitoral maior que zero.')
    qp = {g:v//qe for g,v in totais.items()}
    vagas = {g:0 for g in totais}; extras = {g:0 for g in totais}
    etapas = {}; rodada = []
    for g in totais:
        lista = sorted(listas[g], key=chave_candidato)
        elegiveis = [c for c in lista if 10*c['votos']>=qe]
        escolhidos = elegiveis[:qp[g]]
        # Empate importa apenas se atravessa a última vaga disponível.
        if escolhidos and len(elegiveis)>len(escolhidos):
            verificar_escolha(escolhidos[-1],elegiveis[len(escolhidos)-1:])
        for c in escolhidos: etapas[c['id']] = 'Quociente partidário'
        vagas[g] = len(escolhidos)
    if sum(vagas.values())>cadeiras:
        raise ValueError('O arredondamento do QE gerou mais vagas iniciais que cadeiras. Revise este cenário de votos muito baixos.')
    for fase in ['Sobras 80% / 20%','Sobras finais']:
        while sum(vagas.values())<cadeiras:
            opcoes=[]
            for g in totais:
                rem = sorted([c for c in listas[g] if c['id'] not in etapas],key=chave_candidato)
                if fase=='Sobras 80% / 20%':
                    if 5*totais[g]<4*qe: continue
                    rem=[c for c in rem if 5*c['votos']>=qe]
                if not rem: continue
                c=rem[0]
                opcoes.append((Fraction(totais[g],qp[g]+extras[g]+1),totais[g],c['votos'],g,c,rem))
            if not opcoes: break
            opcoes.sort(key=lambda o:o[:3],reverse=True)
            melhor = opcoes[0]
            if len(opcoes)>1 and opcoes[1][:3]==melhor[:3]:
                raise EmpatePendente('Empate entre agremiações nas médias, votos totais e votos do candidato: '+melhor[3]+' / '+opcoes[1][3]+'. Ajuste o cenário; nenhuma vaga foi decidida arbitrariamente.')
            media,v,cv,g,c,rem = melhor
            verificar_escolha(c,rem)
            denominador=qp[g]+extras[g]+1
            etapas[c['id']] = fase; extras[g]+=1; vagas[g]+=1
            rodada.append({'Rodada':len(rodada)+1,'Etapa':fase,'Grupo':g,'Candidato':c['nome'],'Votos do grupo':v,'Divisor':denominador,'Média':float(media),'Média exata':str(media)})
    saida=[]
    for g in totais:
        ordem=sorted(listas[g],key=chave_candidato); suplencia=0
        for pos,c in enumerate(ordem,1):
            eleito=c['id'] in etapas
            if not eleito and vagas[g]>0: suplencia+=1
            saida.append({**c,'posicao':pos,'eleito':eleito,'etapa':etapas.get(c['id'],''),'suplencia':suplencia if not eleito and vagas[g]>0 else None,'situacao_resultado':'Eleito no cenário' if eleito else ('Suplente no cenário' if vagas[g]>0 else 'Não eleito no cenário')})
    for c in candidatos:
        if not c['considerar']: saida.append({**c,'posicao':None,'eleito':False,'etapa':'','suplencia':None,'situacao_resultado':'Excluído do cenário'})
    resumo=[]
    for g,v in totais.items():
        resumo.append({'Grupo':g,'Votos válidos':v,'Quociente partidário':qp[g],'Vagas pelo QP':sum(1 for c in listas[g] if etapas.get(c['id'])=='Quociente partidário'),'Sobras 80% / 20%':sum(1 for c in listas[g] if etapas.get(c['id'])=='Sobras 80% / 20%'),'Sobras finais':sum(1 for c in listas[g] if etapas.get(c['id'])=='Sobras finais'),'Cadeiras':vagas[g]})
    return {'qe':qe,'total':total,'cadeiras':cadeiras,'preenchidas':sum(vagas.values()),'resumo':sorted(resumo,key=lambda x:(-x['Cadeiras'],-x['Votos válidos'],x['Grupo'])),'candidatos':saida,'rodadas':rodada,'min10':(qe+9)//10,'min20':(qe+4)//5,'min80':(4*qe+4)//5}
