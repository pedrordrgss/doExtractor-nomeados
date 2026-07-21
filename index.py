# import re
# import pandas as pd

# def processar_decretos(caminho_txt, caminho_saida_csv):
#     with open(caminho_txt, 'r', encoding='utf-8') as f:
#         texto = f.read()

#     # Corrige palavras quebradas por hífen e nova linha
#     texto = re.sub(r'-\n\s*', '-', texto)
    
#     blocos = texto.split('DATE: ')
#     dados = []

#     # Nova regex: prevê algarismos romanos (incisos) e limita o símbolo a caracteres alfanuméricos e hífens
#     regex_itens = r'(?:[IVXLCDM]+\s*-\s*)?(?:(\d+\s*\([^)]+\))\s*)?(?:cargos? em comissão de|Função Gratifi cada de|cargo de) (.*?), símbolo ([A-Z0-9-]+)(?:.*?passando a denominar[- ]*se\s+([^;.,]+))?'

#     for bloco in blocos[1:]:
#         data_match = re.search(r'^(\d{4}-\d{2}-\d{2})', bloco)
#         data = data_match.group(1) if data_match else None

#         artigos = re.findall(r'(Art\. \d+º.*?)(?=(?:Art\. \d+º)|Palácio|$)', bloco, re.DOTALL)

#         for art in artigos:
#             art_txt = ' '.join(art.replace('\n', ' ').split())
            
#             if 'Fica alocado' in art_txt:
#                 qtd_match = re.search(r'(\d+\s*\([^)]+\))', art_txt)
#                 quantidade = qtd_match.group(1) if qtd_match else '1'
                
#                 destino_match = re.search(r'alocado.*?(?:da|do) (.*?)(?:,)', art_txt)
#                 destino = destino_match.group(1).strip() if destino_match else '-'
                
#                 cargo_simbolo = re.search(r'(?:cargo em comissão de|Função Gratifi cada de) (.*?), símbolo ([A-Z0-9-]+)', art_txt)
                
#                 if cargo_simbolo:
#                     cargo = cargo_simbolo.group(1).strip()
#                     simbolo = cargo_simbolo.group(2).strip()
#                 else:
#                     cargo = '-'
#                     simbolo = '-'
                
#                 dados.append({
#                     'Data': data,
#                     'Ato': 'Alocação',
#                     'Cargo': cargo,
#                     'Quantidade': quantidade,
#                     'Símbolo': simbolo,
#                     'Origem': '-',
#                     'Destino': destino,
#                     'Nova Denominação': '-'
#                 })

#             elif 'Fica transferido' in art_txt:
#                 locais = re.search(r'transferido.*? da (.*?) para o.*? da (.*?)[,.]', art_txt)
#                 origem = locais.group(1).strip() if locais else '-'
#                 destino = locais.group(2).strip() if locais else '-'

#                 itens = re.finditer(regex_itens, art_txt)

#                 for item in itens:
#                     qtd = item.group(1) if item.group(1) else '1'
#                     cargo = item.group(2).strip()
#                     simbolo = item.group(3).strip()
                    
#                     nova_denom = item.group(4).strip() if item.group(4) else '-'
#                     if nova_denom.endswith(' e'):
#                         nova_denom = nova_denom[:-2].strip()

#                     dados.append({
#                         'Data': data,
#                         'Ato': 'Transferência',
#                         'Cargo': cargo,
#                         'Quantidade': qtd,
#                         'Símbolo': simbolo,
#                         'Origem': origem,
#                         'Destino': destino,
#                         'Nova Denominação': nova_denom
#                     })
                    
#             elif re.search(r'denominar[- ]*se', art_txt):
#                 itens = re.finditer(regex_itens, art_txt)

#                 for item in itens:
#                     qtd = item.group(1) if item.group(1) else '1'
#                     cargo = item.group(2).strip()
#                     simbolo = item.group(3).strip()
                    
#                     nova_denom = item.group(4).strip() if item.group(4) else '-'
#                     if nova_denom.endswith(' e'):
#                         nova_denom = nova_denom[:-2].strip()

#                     dados.append({
#                         'Data': data,
#                         'Ato': 'Redenominação',
#                         'Cargo': cargo,
#                         'Quantidade': qtd,
#                         'Símbolo': simbolo,
#                         'Origem': '-',
#                         'Destino': '-',
#                         'Nova Denominação': nova_denom
#                     })

#     df = pd.DataFrame(dados)
#     ordem_colunas = ['Data', 'Ato', 'Cargo', 'Quantidade', 'Símbolo', 'Origem', 'Destino', 'Nova Denominação']
#     df = df[ordem_colunas]
    
#     df.to_csv(caminho_saida_csv, index=False, encoding='utf-8')
#     print(f"Extração concluída. Arquivo salvo em: {caminho_saida_csv}")
#     return df

# processar_decretos('saida.txt', 'tabela_cargos.csv')



import re
import pandas as pd

def processar_decretos(caminho_txt, caminho_saida_csv):
    with open(caminho_txt, 'r', encoding='utf-8') as f:
        texto = f.read()

    texto = re.sub(r'-\n\s*', '-', texto)
    
    blocos = texto.split('DATE: ')
    dados = []

    regex_itens = r'(?:[IVXLCDM]+\s*-\s*)?(?:(\d+\s*\([^)]+\))\s*)?(?:cargos? em comissão de|Função Gratifi cada de|cargo de) (.*?), símbolo ([A-Z0-9-]+)(?:.*?passando a denominar[- ]*se\s+([^;.,]+))?'

    for bloco in blocos[1:]:
        data_match = re.search(r'^(\d{4}-\d{2}-\d{2})', bloco)
        data = data_match.group(1) if data_match else None

        artigos = re.findall(r'(Art\. \d+º.*?)(?=(?:Art\. \d+º)|Palácio|$)', bloco, re.DOTALL)

        for art in artigos:
            art_txt = ' '.join(art.replace('\n', ' ').split())
            
            if re.search(r'Ficam? alocados?', art_txt):
                qtd_match = re.search(r'(\d+\s*\([^)]+\))', art_txt)
                quantidade = qtd_match.group(1) if qtd_match else '1'
                
                destino_match = re.search(r'alocados?\s+(.*?)(?:,| os cargos| \d+\s*\()', art_txt)
                if destino_match:
                    destino = re.sub(r'^.*?Qua-?dro.*?(?:da|do)\s+', '', destino_match.group(1)).strip()
                    destino = re.sub(r'^(?:no |na |o |a |do |da |de )', '', destino).strip()
                else:
                    destino = '-'
                
                cargo_simbolo = re.search(r'(?:cargo em comissão de|Função Gratifi cada de) (.*?), símbolo ([A-Z0-9-]+)', art_txt)
                
                if cargo_simbolo:
                    cargo = cargo_simbolo.group(1).strip()
                    simbolo = cargo_simbolo.group(2).strip()
                else:
                    cargo = '-'
                    simbolo = '-'
                
                dados.append({
                    'Data': data,
                    'Ato': 'Alocação',
                    'Cargo': cargo,
                    'Quantidade': quantidade,
                    'Símbolo': simbolo,
                    'Origem': '-',
                    'Destino': destino,
                    'Nova Denominação': '-'
                })

            elif re.search(r'Ficam? transferidos?', art_txt):
                locais = re.search(r'transferidos?\s+(.*?)\s+para\s+(.*?)(?:,| os cargos| \d+\s*\()', art_txt)
                if locais:
                    origem = re.sub(r'^.*?Qua-?dro.*?(?:da|do)\s+', '', locais.group(1)).strip()
                    origem = re.sub(r'^(?:do |da |de )', '', origem).strip()
                    
                    destino = re.sub(r'^.*?Qua-?dro.*?(?:da|do)\s+', '', locais.group(2)).strip()
                    destino = re.sub(r'^(?:o |a |do |da |de )', '', destino).strip()
                else:
                    origem = '-'
                    destino = '-'

                itens = re.finditer(regex_itens, art_txt)

                for item in itens:
                    qtd = item.group(1) if item.group(1) else '1'
                    cargo = item.group(2).strip()
                    simbolo = item.group(3).strip()
                    
                    nova_denom = item.group(4).strip() if item.group(4) else '-'
                    if nova_denom.endswith(' e'):
                        nova_denom = nova_denom[:-2].strip()

                    dados.append({
                        'Data': data,
                        'Ato': 'Transferência',
                        'Cargo': cargo,
                        'Quantidade': qtd,
                        'Símbolo': simbolo,
                        'Origem': origem,
                        'Destino': destino,
                        'Nova Denominação': nova_denom
                    })
                    
            elif re.search(r'denominar[- ]*se', art_txt):
                itens = re.finditer(regex_itens, art_txt)

                for item in itens:
                    qtd = item.group(1) if item.group(1) else '1'
                    cargo = item.group(2).strip()
                    simbolo = item.group(3).strip()
                    
                    nova_denom = item.group(4).strip() if item.group(4) else '-'
                    if nova_denom.endswith(' e'):
                        nova_denom = nova_denom[:-2].strip()

                    dados.append({
                        'Data': data,
                        'Ato': 'Redenominação',
                        'Cargo': cargo,
                        'Quantidade': qtd,
                        'Símbolo': simbolo,
                        'Origem': '-',
                        'Destino': '-',
                        'Nova Denominação': nova_denom
                    })

    df = pd.DataFrame(dados)
    ordem_colunas = ['Data', 'Ato', 'Cargo', 'Quantidade', 'Símbolo', 'Origem', 'Destino', 'Nova Denominação']
    df = df[ordem_colunas]
    
    df.to_csv(caminho_saida_csv, index=False, encoding='utf-8')
    print(f"Extração concluída. Arquivo salvo em: {caminho_saida_csv}")
    return df

processar_decretos('saida.txt', 'tabela_cargos.csv')