import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "data", "NHANES", "2005-2006")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "data_cleaned", "nhanes_myopia_cleaned.csv")

DEMO_COLS = ['SEQN', 'RIDAGEYR', 'RIAGENDR', 'RIDRETH1', 'INDFMPIR']

VIX_TARGET_COLS = ['SEQN', 'VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']
VIX_OPTIONAL_COLS = ['VIDRVA', 'VIDLVA', 'VIXKRMM', 'VIXKLMM']
REFRACTION_COLS = ['VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']

BMX_COLS = ['SEQN', 'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST']

VIT_D_CANDIDATES = ['LBDVIDMS', 'LBXVIDMS', 'LBDVID', 'LBXVID']

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