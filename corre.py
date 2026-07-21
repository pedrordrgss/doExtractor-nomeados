import re

def unir_gratifi(caminho_entrada, caminho_saida):
    with open(caminho_entrada, 'r', encoding='utf-8') as f:
        texto = f.read()
    
    texto_modificado = re.sub(r'([Ee]specifi)\s+(\w+)', r'\1\2', texto)
    
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(texto_modificado)

unir_gratifi('saida.txt', 'retorno.txt')