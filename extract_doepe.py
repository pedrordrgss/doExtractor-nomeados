"""
DOE-PE Extractor
Extracts decree excerpts starting with "ATOS DO DIA" and ending at "Secretarias de Estado".
"""

import re
import csv
import time
import logging
from datetime import date, timedelta
from pathlib import Path

import requests
import pdfplumber
from fpdf import FPDF

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

START_DATE = date(2023, 1, 1)
END_DATE   = date(2023, 1, 10)

# Estrutura do link oficial do Diário Oficial de PE hospedado no AWS S3
URL_TEMPLATE = (
    "https://cepebr-prod.s3.amazonaws.com/1/cadernos/"
    "{year}/{year}{month}{day}/1-PoderExecutivo/PoderExecutivo({year}{month}{day}).pdf"
)

# Marcadores textuais para identificar o início e o fim dos decretos de interesse
START_PATTERNS = re.compile(r"(ATOS DO DIA )", re.IGNORECASE)
END_MARKER = "Secretarias de Estado"

OUTPUT_CSV = Path("doe_pe_extracts.csv")
OUTPUT_TXT = Path("doe_pe_extracts.txt")
OUTPUT_PDF = Path("doe_pe_extracts.pdf")

REQUEST_TIMEOUT  = 30
DELAY_BETWEEN_REQUESTS = 1.5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_excerpt(raw_text: str) -> str:
    """Filtra o texto bruto, removendo cabeçalhos de página e unificando os atos."""
    # Isola o cabeçalho principal até a palavra "RESOLVE:"
    header_match = re.search(r"(ATOS DO DIA[\s\S]*?RESOLVE:)", raw_text, re.IGNORECASE)
    header = header_match.group(1).strip() if header_match else "ATOS DO DIA"
    
    # Captura individualmente cada ato (blocos iniciando em "Nº" e indo até o ponto final)
    atos_encontrados = re.findall(r"(Nº\s*\d+[\s\S]*?\.\s)", raw_text)
    
    # Remove quebras de linha órfãs e espaços duplicados dentro de cada ato
    atos_limpos = [re.sub(r'\s+', ' ', ato).strip() for ato in atos_encontrados]
    
    return header + "\n\n" + "\n\n".join(atos_limpos)

def build_url(d: date) -> str:
    """Formata a URL dinamicamente com base na data fornecida."""
    return URL_TEMPLATE.format(year=d.strftime("%Y"), month=d.strftime("%m"), day=d.strftime("%d"))

def download_pdf(url: str) -> bytes | None:
    """Faz a requisição HTTP para baixar o arquivo PDF."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response.content if response.status_code == 200 else None
    except requests.RequestException:
        return None

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extrai o texto dividindo a página em duas colunas para manter a ordem correta de leitura."""
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            # Divide a página ao meio verticalmente (coluna esquerda e coluna direita)
            left = page.crop((0, 0, page.width/2, page.height)).extract_text()
            right = page.crop((page.width/2, 0, page.width, page.height)).extract_text()
            
            # Junta o texto mantendo o fluxo natural de leitura (esquerda depois direita)
            page_text = (left or "") + "\n" + (right or "")
            if page_text.strip(): text_parts.append(page_text)
    return "\n".join(text_parts)

def find_excerpts(text: str) -> list[str]:
    """Localiza todos os trechos que começam com o padrão inicial e terminam no marcador final."""
    excerpts = []
    search_from = 0
    while True:
        match = START_PATTERNS.search(text, search_from)
        if not match: break  # Para o loop se não houver mais ocorrências
        
        # Encontra o fim do bloco a partir do início do trecho atual
        end_pos = text.find(END_MARKER, match.start())
        if end_pos == -1:
            excerpts.append(text[match.start():].strip())
            break
            
        excerpt = text[match.start():end_pos + len(END_MARKER)].strip()
        excerpts.append(excerpt)
        search_from = end_pos + len(END_MARKER) # Avança o ponteiro de busca
    return excerpts

def iter_dates(start: date, end: date):
    """Gerador para iterar dia a dia entre o intervalo definido."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def generate_pdf(txt_path: Path, pdf_path: Path):
    """Gera um PDF consolidado com formatação de texto segura a partir do arquivo TXT."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    with txt_path.open("r", encoding="utf-8") as f:
        for line in f:
            # Substitui caracteres especiais do UTF-8 para evitar quebras no encoding Latin-1 do FPDF
            linha_segura = line.replace("–", "-").replace("—", "-").encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(190, 5, linha_segura.rstrip())
    pdf.output(str(pdf_path))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Orquestra o fluxo de download, extração, limpeza e escrita dos dados."""
    with (
        OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file,
        OUTPUT_TXT.open("w", encoding="utf-8") as txt_file,
    ):
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(["date", "excerpt_number", "excerpt"])
        
        # Percorre o calendário dia após dia
        for d in iter_dates(START_DATE, END_DATE):
            pdf_bytes = download_pdf(build_url(d))
            if not pdf_bytes: continue  # Pula dias sem diário publicado (ex: finais de semana)
            
            # Extrai o texto bruto e localiza os trechos de interesse
            raw_excerpts = find_excerpts(extract_text_from_pdf_bytes(pdf_bytes))
            
            # Trata, limpa e salva cada trecho encontrado
            for i, raw_excerpt in enumerate(raw_excerpts, start=1):
                excerpt = clean_excerpt(raw_excerpt)
                writer.writerow([str(d), i, excerpt])
                txt_file.write(f"DATE: {d} | EXCERPT #{i}\n{'-'*80}\n{excerpt}\n\n")
                txt_file.flush()
                
            # Pausa educada para evitar bloqueios no servidor
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Compila o arquivo TXT final em um formato PDF estruturado
    generate_pdf(OUTPUT_TXT, OUTPUT_PDF)
    log.info("Processamento concluído.")

if __name__ == "__main__":
    main()