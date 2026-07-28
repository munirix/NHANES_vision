import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NHANES_DIR = os.path.join(BASE_DIR, "data", "NHANES")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "data_cleaned")
CYCLE_DIR = os.path.join(CLEANED_DIR, "cycles")
OUTPUT_FILE = os.path.join(CLEANED_DIR, "nhanes_myopia_cleaned.csv")

# Ciclos históricos do NHANES e o sufixo de arquivo padrão do CDC.
# O diretório de cada ciclo em data/NHANES leva o nome do próprio ciclo.
CYCLES = [
    {"name": "1999-2000", "suffix": ""},
    {"name": "2001-2002", "suffix": "_B"},
    {"name": "2003-2004", "suffix": "_C"},
    {"name": "2005-2006", "suffix": "_D"},
    {"name": "2007-2008", "suffix": "_E"},
]

# Componentes obrigatórios para que um ciclo possa ser consolidado
REQUIRED_COMPONENTS = ['DEMO', 'VIX', 'BMX']

DEMO_COLS = ['SEQN', 'RIDAGEYR', 'RIAGENDR', 'RIDRETH1', 'INDFMPIR']

VIX_TARGET_COLS = ['SEQN', 'VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']
VIX_OPTIONAL_COLS = ['VIXORAM', 'VIXOLAM', 'VIDRVA', 'VIDLVA', 'VIXKRMM', 'VIXKLMM']
REFRACTION_COLS = ['VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']
AXIS_COLS = ['VIXORAM', 'VIXOLAM']

BMX_COLS = ['SEQN', 'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST']

VIT_D_CANDIDATES = ['LBDVIDMS', 'LBXVIDMS', 'LBDVID', 'LBXVID']

# Códigos de anomalia do NHANES que significam "Could not obtain".
# Sem a substituição por NaN o modelo leria 88 dioptrias como medida real.
REFRACTION_INVALID_CODE = 88
AXIS_INVALID_CODE = 888

# Harmonização do top-coding de idade: os ciclos de 1999 a 2006 truncam a idade
# em 85 anos, enquanto 2007-2008 trunca em 80. Aplicamos um corte uniforme em 80
# para evitar anomalias na curva de idade entre ciclos.
AGE_TOP_CODE = 80

MYOPIA_THRESHOLD_LOW = -0.5
MYOPIA_THRESHOLD_HIGH = -6.0

COLUMN_RENAME = {
    'RIDAGEYR': 'AGE',
    'RIDRETH1': 'ETHNICITY',
    'INDFMPIR': 'INCOME_PIR',
    'BMXWT': 'WEIGHT_KG',
    'BMXHT': 'HEIGHT_CM',
    'BMXBMI': 'BMI',
    'BMXWAIST': 'WAIST_CIRC_CM'
}

CLASS_NAMES = {
    0: "Sem Miopia",
    1: "Miopia Leve/Moderada",
    2: "Alta Miopia"
}

def cycle_output_file(cycle_name):
    return os.path.join(CYCLE_DIR, f"nhanes_myopia_{cycle_name}.csv")