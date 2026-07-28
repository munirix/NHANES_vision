import os
import pandas as pd
import config

def _read_sas(filename):
    path = os.path.join(config.RAW_DIR, filename)
    return pd.read_sas(path, format="xport")

def load_demographic_data():
    print("[1/4] Carregando dados demográficos "+config.RAW_DIR[-9:]+" (DEMO_D.XPT)...")
    df = _read_sas("DEMO_D.XPT")
    df = df[config.DEMO_COLS].copy()
    print(f"       -> {len(df)} registros carregados.")
    return df

def load_vision_data():
    print("[2/4] Carregando dados do exame de visão "+config.RAW_DIR[-9:]+" (VIX_D.XPT)...")
    df = _read_sas("VIX_D.XPT")

    available_optional = [col for col in config.VIX_OPTIONAL_COLS if col in df.columns]
    df = df[config.VIX_TARGET_COLS + available_optional].copy()

    print(f"       -> {len(df)} registros carregados.")
    return df

def load_anthropometric_data():
    print("[3/4] Carregando dados antropométricos "+config.RAW_DIR[-9:]+" (BMX_D.XPT)...")
    df = _read_sas("BMX_D.XPT")
    selected_cols = [col for col in config.BMX_COLS if col in df.columns]
    df = df[selected_cols].copy()
    print(f"       -> {len(df)} registros carregados.")
    return df

def load_vitamin_d_data():
    print("[4/4] Carregando dados de laboratório de Vitamina D "+config.RAW_DIR[-9:]+" (VID_D.XPT)...")
    try:
        df_raw = _read_sas("VID_D.XPT")
    except Exception as e:
        print(f"       [!] Nota: Não foi possível processar VID_D.XPT ({e}). O pipeline continuará sem os níveis séricos de Vitamina D.")
        return pd.DataFrame(), False

    vit_d_col = None
    for candidate in config.VIT_D_CANDIDATES:
        if candidate in df_raw.columns:
            vit_d_col = candidate
            break
            
    if not vit_d_col:
        print("       [!] Coluna de Vitamina D não identificada de forma padrão. Continuando sem Vitamina D sérica.")
        return pd.DataFrame(), False
        
    df = df_raw[['SEQN', vit_d_col]].copy()
    df.rename(columns={vit_d_col: 'VITAMIN_D_LEVEL'}, inplace=True)
    print(f"       -> {len(df)} registros carregados (usando coluna '{vit_d_col}').")
    return df, True