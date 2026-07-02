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

DATES_LIST = [
    date(2026, 1, 8),
    date(2026, 1, 16),
    date(2026, 1, 17),
    date(2026, 1, 21),
    date(2026, 1, 22),
    date(2026, 1, 29),
    date(2026, 1, 31),
    date(2026, 2, 4),
    date(2026, 2, 7),
    date(2026, 2, 10),
    date(2026, 2, 11),
    date(2026, 2, 13),
    date(2026, 2, 21),
    date(2026, 2, 25),
    date(2026, 2, 28),
    date(2026, 3, 5),
    date(2026, 3, 12),
    date(2026, 3, 13),
    date(2026, 3, 17),
    date(2026, 3, 19),
    date(2026, 3, 20),
    date(2026, 3, 21),
    date(2026, 3, 24),
    date(2026, 3, 27),
    date(2026, 4, 7),
    date(2026, 4, 9),
    date(2026, 4, 10),
    date(2026, 4, 15),
    date(2026, 4, 16),
    date(2026, 4, 17),
    date(2026, 4, 18),
    date(2026, 4, 23),
    date(2026, 4, 28),
    date(2026, 4, 29),
    date(2026, 4, 30),
    date(2026, 5, 1),
    date(2026, 5, 9),
    date(2026, 5, 12),
    date(2026, 5, 15),
    date(2026, 5, 16),
    date(2026, 5, 20),
    date(2026, 5, 23),
    date(2026, 5, 26),
    date(2026, 5, 28),
    date(2026, 5, 30),
    date(2026, 6, 3),
]

#START_DATE = date(2026, 4, 28)
#END_DATE   = date(2026, 4, 28)

# Lista de Atos desejados (ex: ["Nomear", "Exonerar", "Designar", "Autorizar", "Cassar", "Conceder", "Concedo", "Converter", "Declarar", "Demitir", "Dispensar", "Exonerar", "Homologar", "Promover", "Prorrogar", "Reconduzir", "Submeter", "Transferir", "Tornar", etc]). Deixe vazia [] para extrair todos.
ATOS_FILTER = ["Nomear", "Exonerar"]

URL_TEMPLATE = (
    "https://cepebr-prod.s3.amazonaws.com/1/cadernos/"
    "{year}/{year}{month}{day}/1-PoderExecutivo/PoderExecutivo({year}{month}{day}).pdf"
)

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
# Extraction & Parsing Logic
# ---------------------------------------------------------------------------

def clean_excerpt(raw_text: str) -> str:
    """Filtra o texto bruto para o TXT original."""
    header_match = re.search(r"(ATOS DO DIA[\s\S]*?RESOLVE:)", raw_text, re.IGNORECASE)
    header = header_match.group(1).strip() if header_match else "ATOS DO DIA"
    atos_encontrados = re.findall(r"(Nº\s*\d+[\s\S]*?(?=(?:Nº\s*\d+|$)))", raw_text, re.IGNORECASE)
    atos_limpos = [re.sub(r'\s+', ' ', ato).strip() for ato in atos_encontrados]
    return header + "\n\n" + "\n\n".join(atos_limpos)

def parse_ato(ato_text: str, date_obj: date) -> dict:
    """Aplica as regras de negócio para fatiar o texto de um ato individual para o CSV."""
    # Corrige erros de aglutinação comuns do texto original
    ato_text = re.sub(r'peloexpediente', 'pelo expediente', ato_text, flags=re.IGNORECASE)
    
    # Protege o hífen de palavras compostas ANTES da limpeza geral
    ato_text = re.sub(r'(Vice)-\s+(Governadoria)', r'\1-\2', ato_text, flags=re.IGNORECASE)

    # Remove espaços extras e junta palavras separadas por hífen de quebra de linha (ex: "Se- cretaria")
    ato_text = re.sub(r'\s+', ' ', ato_text).strip()
    ato_text = re.sub(r'([A-Za-zÀ-ÿ])- ([A-Za-zÀ-ÿ])', r'\1\2', ato_text)



    res = {
        "Data": date_obj.strftime("%d/%m/%Y"),
        "Número": "",
        "Ato": "",
        "Nome": "",
        "Cargo": "",
        "Símbolo": "",
        "Órgão": ""
    }
    
    num_match = re.search(r"(Nº\s*\d+)", ato_text)
    if num_match:
        res["Número"] = num_match.group(1).strip()
        end_num = num_match.end()
        
        ato_match = re.search(r"^[-\s–—,:]*([A-Za-zÀ-ÿ]+)", ato_text[end_num:])
        if ato_match:
            res["Ato"] = ato_match.group(1).strip()
            ato_lower = res["Ato"].lower()
            
            ato_word_pos = ato_text.find(res["Ato"], end_num)
            remainder = ato_text[ato_word_pos + len(res["Ato"]):].strip()
            
            # Isolamento e extração robusta do Nome baseado em delimitadores finais
            if ato_lower not in ["tornar", "retificar"]:
                # Isolamento e extração do Nome corrigido (sem quebra em partículas como 'da/do')
                delim_pattern = r"(,?\s*matr[ií]cula|\s+para\s+exercer|\s+para\s+o\s+cargo|\s+do\s+cargo|\s+da\s+Fun[çc]ãO|\s+de\s+Fun[çc]ãO|,\s*na\s+qualidade|\s+para\s+participar|,\s*sem\s+ônus|,\s*com\s+ônus|\s+da\s+Empresa|\s+do\s+Departamento|\s+da\s+Secretaria)"
                parts = re.split(delim_pattern, remainder, maxsplit=1, flags=re.IGNORECASE)
                name_phrase = parts[0].strip()
                
                if "," in name_phrase:
                    sub_parts = [p.strip() for p in name_phrase.split(",") if p.strip()]
                    if sub_parts:
                        name_phrase = sub_parts[-1]
                
                name_phrase = re.sub(r"^(o\s+servidor|a\s+servidora|o\s+Promotor\s+de\s+Justi[çc]a|de\s+|a\s+)\s*", "", name_phrase, flags=re.IGNORECASE).strip()
                res["Nome"] = name_phrase

    # Extração de Cargo adaptada para tolerar vírgulas inesperadas (ex: "cargo em comissão, de")
    # Extração de Cargo reformulada para aceitar livremente espaços, vírgulas e preposições
    cargo_match = re.search(r"(?:cargo em comiss[ão]|cargo de|comiss[ão]o|Fun[çc]ãO Gratificada de|responder pelo expediente d[ao]|compor o)[\s,]+(?:de\s+)?([^,]+)", ato_text, re.IGNORECASE)
    if cargo_match:
        res["Cargo"] = cargo_match.group(1).strip()
        res["Cargo"] = re.split(r"\s+s[íi]mbolo", res["Cargo"], flags=re.IGNORECASE)[0].strip()

    # Extração de Símbolo com captura do índice final    
    simbolo_match = re.search(r"s[íi]mbolo\s*[-:]?\s*([A-Z0-9/a-z]+\s*-\s*\d+|[A-Z0-9/a-z-]+)", ato_text, re.IGNORECASE)
    simbolo_end = 0
    if simbolo_match:
        res["Símbolo"] = simbolo_match.group(1).replace(" ", "").strip()
        simbolo_end = simbolo_match.end()
        
    # Extração de Órgão com a inclusão de "Junta"
    orgao_keywords = r"(Secretaria|Empresa|Instituto|Universidade|Conservatório|Fundação|Tribunal|Casa|Procuradoria|Agência|Companhia|Defensoria|Polícia|Vice-Governadoria|Governadoria|Departamento|Programa|Distrito|Junta|Conselho|Gabinete)"
    # Define de onde começar a busca do órgão
    text_for_orgao = ato_text[simbolo_end:] if simbolo_end > 0 else ato_text
    orgao_match = re.search(r"\b" + orgao_keywords + r"\b.*?(?=(?:,\s*(?:da\s+|do\s+)?com\s+efeito|,\s*a\s+partir|,\s*s[íi]mbolo|,\s*matr[ií]cula|,\s*para|,\s*no\s+per[ií]odo|,\s*em\s+gozo|\.|$))", text_for_orgao, re.IGNORECASE)
    
    if orgao_match:
        res["Órgão"] = orgao_match.group(0).strip()
    elif simbolo_end > 0:
        # Fallback de segurança buscando no texto inteiro
        orgao_match_fallback = re.search(r"\b" + orgao_keywords + r"\b.*?(?=(?:,\s*(?:da\s+|do\s+)?com\s+efeito|,\s*a\s+partir|,\s*s[íi]mbolo|,\s*matr[ií]cula|,\s*para|,\s*no\s+per[ií]odo|,\s*em\s+gozo|\.|$))", ato_text, re.IGNORECASE)
        if orgao_match_fallback:
            res["Órgão"] = orgao_match_fallback.group(0).strip()
            
    # Se o símbolo for exclusivamente "DAS", o Órgão recebe o mesmo valor do Cargo
    if res["Símbolo"] == "DAS":
        res["Órgão"] = res["Cargo"]
        
    
    return res

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_url(d: date) -> str:
    return URL_TEMPLATE.format(year=d.strftime("%Y"), month=d.strftime("%m"), day=d.strftime("%d"))

def download_pdf(url: str) -> bytes | None:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response.content if response.status_code == 200 else None
    except requests.RequestException:
        return None

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            left = page.crop((0, 0, page.width/2, page.height)).extract_text()
            right = page.crop((page.width/2, 0, page.width, page.height)).extract_text()
            page_text = (left or "") + "\n" + (right or "")
            if page_text.strip(): text_parts.append(page_text)
    return "\n".join(text_parts)

def find_excerpts(text: str) -> list[str]:
    expts = []
    search_from = 0
    while True:
        match = START_PATTERNS.search(text, search_from)
        if not match: break
        end_pos = text.find(END_MARKER, match.start())
        if end_pos == -1:
            expts.append(text[match.start():].strip())
            break
        excerpt = text[match.start():end_pos + len(END_MARKER)].strip()
        expts.append(excerpt)
        search_from = end_pos + len(END_MARKER)
    return expts

def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def generate_pdf(txt_path: Path, pdf_path: Path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    with txt_path.open("r", encoding="utf-8") as f:
        for line in f:
            linha_segura = line.replace("–", "-").replace("—", "-").encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(190, 5, linha_segura.rstrip())
    pdf.output(str(pdf_path))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with (
        OUTPUT_CSV.open("w", newline="", encoding="utf-8") as csv_file,
        OUTPUT_TXT.open("w", encoding="utf-8") as txt_file,
    ):
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(["Data", "Número", "Ato", "Nome", "Cargo", "Símbolo", "Órgão"])
        
        #for d in iter_dates(START_DATE, END_DATE):
        for d in DATES_LIST:
            log.info(f"Buscando PDF da data: {d}...")
            pdf_bytes = download_pdf(build_url(d))
            if not pdf_bytes:
                log.info(f"Nenhum diário encontrado para {d}.")
                continue
                
            log.info(f"PDF baixado para {d}. Processando trechos...")
            raw_excerpts = find_excerpts(extract_text_from_pdf_bytes(pdf_bytes))
            
            for i, raw_excerpt in enumerate(raw_excerpts, start=1):
                excerpt = clean_excerpt(raw_excerpt)
                txt_file.write(f"DATE: {d} | EXCERPT #{i}\n{'-'*80}\n{excerpt}\n\n")
                txt_file.flush()
                
                atos_encontrados = re.findall(r"(Nº\s*\d+[\s\S]*?(?=(?:Nº\s*\d+|$)))", raw_excerpt, re.IGNORECASE)
                for ato_raw in atos_encontrados:
                    parsed = parse_ato(ato_raw, d)
                    if ATOS_FILTER and parsed["Ato"].strip().lower() not in [a.lower() for a in ATOS_FILTER]:
                        continue
                    writer.writerow([
                        parsed["Data"],
                        parsed["Número"],
                        parsed["Ato"],
                        parsed["Nome"],
                        parsed["Cargo"],
                        parsed["Símbolo"],
                        parsed["Órgão"]
                    ])
                    
            time.sleep(DELAY_BETWEEN_REQUESTS)

    generate_pdf(OUTPUT_TXT, OUTPUT_PDF)
    log.info("Processamento concluído.")


if __name__ == "__main__":
    main()