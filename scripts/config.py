"""
config.py

Hame-ye knob-haye project ye ja.

CHERA IN FILE ALAN SAKHTE SHOD (va na az avval)
-----------------------------------------------
Ta hala EMBEDDING_DIM tuye 4 ta file tekrar mishod. Ta vaghti hich
vaght avazesh nemikardim, moshkeli nabud.

Vali hala mikhaym experiment konim: 768 ya 3072? k=3 ya k=8? Flash ya
Pro? Age har experiment ya'ni 4 ta file avaz kardan, ya eshtebah
mikoni (yeki ro ja mindazi va natije bi-ma'ni mishe) ya tanbali mikoni
va aslan emtehan nemikoni.

DARS: refactor vaghti anjam mishe ke tekrar VAGHEAN azaret bede - na
az avval "mahz-e ehtiat". Age az rooz-e aval in file ro sakhte budim,
ye laye-ye ezafi bud baraye chizi ke hanuz moshkel nabud.
"""

from pathlib import Path

# --- masir-ha ---
# MASIR-E MOTLAGH, NA NESBI
# -------------------------
# Aval Path("data") bud - masir-e NESBI, ya'ni nesbat be jaii ke
# command ro zadi (working directory). Faghat vaghti kar mikard ke
# daghighan az root-e project run mikardi.
#
# __file__ = masir-e hamin file-e config.py
# .resolve() = masir-e kamel va motlagh
# .parent    = scripts/
# .parent    = root-e project
#
# Hala mohem nist az koja run mishe - masir hamishe dorost-e.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SITE_PATH = DATA_DIR / "index.html"
CHUNKS_PATH = DATA_DIR / "chunks.json"
INDEX_PATH = DATA_DIR / "index.json"

# --- embedding ---
EMBEDDING_MODEL = "gemini-embedding-001"

# Default-e in model 3072-e.
#
# EMTEHAN SHOD (Aug 2026): 3072 ro rooye hamun golden set zadim.
#   768  -> recall@1 75.0% | recall@3 95.8% | recall@8 100%
#   3072 -> recall@1 70.8% | recall@3 95.8% | recall@8 100%
#
# Ya'ni 4 barabar dimension NA komak kard, balke recall@1 kami oft
# kard. (Ba 12 soal, in fargh dar vaghe YE soal-e - pas nemishe goft
# "3072 badtar-e". Mishe goft "behtar nist va gerun-tar-e", va hamin
# baraye tasmim kafie.)
#
# Ehtemal-e tozih: tuye faza-ye ba dimension-e balatar, chunk-haye
# bishtari mitunan "kami shabih" bashan - etela'at-e ezafe bishtar
# noise ovord ta signal.
#
# NATIJE-YE MOHEM-TAR: dimension gluogah nabud. Moshkel-e ma ORDERING
# hast (recall@8 = 100% ya'ni hame javab-ha peyda mishan), na etela'at.
EMBEDDING_DIM = 768

# --- retrieval ---
# Chand chunk be model dade beshe. Ba eval tune mishe, na ba hads.
TOP_K = 8

# --- generation ---
# Ba `python scripts/list_models.py` check kon ke hanuz mojud bashe.
GENERATION_MODEL = "gemini-2.5-flash"

# 0 = hamishe hamun javab az hamun context. Baraye eval lazem-e:
# age har bar javab avaz she, nemituni begi behtar shod ya na.
TEMPERATURE = 0.0
