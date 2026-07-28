import numpy as np
import pandas as pd
import config

def harmonize_age(df):
    """Harmoniza o top-coding da idade entre ciclos aplicando o corte uniforme
    definido em config.AGE_TOP_CODE (1999-2006 truncam em 85, 2007-2008 em 80)."""
    df = df.copy()
    if 'RIDAGEYR' in df.columns:
        df['RIDAGEYR'] = df['RIDAGEYR'].clip(upper=config.AGE_TOP_CODE)
    return df

def clean_refraction_values(df):
    """Substitui por NaN os códigos de 'Could not obtain' do exame refrativo:
    88 nas esferas/cilindros e 888 nos eixos de astigmatismo."""
    df = df.copy()
    for col in config.REFRACTION_COLS:
        if col in df.columns:
            df.loc[df[col] == config.REFRACTION_INVALID_CODE, col] = np.nan
    for col in config.AXIS_COLS:
        if col in df.columns:
            df.loc[df[col] == config.AXIS_INVALID_CODE, col] = np.nan
    return df

def calculate_spherical_equivalent(df):
    df = df.copy()
    df['SE_RIGHT'] = df['VIXORSM'] + (df['VIXORCM'] / 2.0)
    df['SE_LEFT'] = df['VIXOLSM'] + (df['VIXOLCM'] / 2.0)
    df['SE_MEAN'] = df[['SE_RIGHT', 'SE_LEFT']].mean(axis=1)
    return df

def filter_valid_refraction(df):
    df_filtered = df.dropna(subset=['SE_MEAN']).copy()
    removed = len(df) - len(df_filtered)
    print(f"       -> {removed} participantes removidos por não realizarem o exame refrativo.")
    print(f"       -> Restaram {len(df_filtered)} registros válidos com exames de visão.")
    return df_filtered

def _classify_myopia(se):
    if se > config.MYOPIA_THRESHOLD_LOW:
        return 0
    elif se >= config.MYOPIA_THRESHOLD_HIGH:
        return 1
    else:
        return 2

def classify_myopia(df):
    df = df.copy()
    df['MYOPIA_CLASS'] = df['SE_MEAN'].apply(_classify_myopia)
    return df

def merge_data_sources(df_vix, df_demo, df_bmx, df_vid=None, has_vit_d=False):
    print("\n--- Mesclando tabelas (Merge por ID do participante)... ---")
    df_consolidado = df_vix
    df_consolidado = pd.merge(df_consolidado, df_demo, on='SEQN', how='inner')
    df_consolidado = pd.merge(df_consolidado, df_bmx, on='SEQN', how='left')
    
    if has_vit_d and df_vid is not None:
        df_consolidado = pd.merge(df_consolidado, df_vid, on='SEQN', how='left')
        
    return df_consolidado

def rename_and_encode(df):
    df = df.copy()
    df['IS_FEMALE'] = (df['RIAGENDR'] == 2).astype(int)
    df.drop(columns=['RIAGENDR'], inplace=True)
    df.rename(columns=config.COLUMN_RENAME, inplace=True)
    return df

def tag_cycle(df, cycle_name):
    """Registra a origem histórica do registro para análises de coorte ou estratificação."""
    df = df.copy()
    df['CYCLE_YEAR'] = cycle_name
    return df

def combine_cycles(dataframes):
    """Concatena os ciclos já processados em uma única base unificada."""
    print(f"\n--- Concatenando {len(dataframes)} ciclos em uma base histórica única... ---")
    return pd.concat(dataframes, ignore_index=True)

def print_distribution(df, label="Consolidação Concluída!"):
    print(f"\n[OK] {label}")
    print(f"       -> Total de instâncias: {len(df)}")
    print(f"       -> Distribuição das classes de miopia:")
    dist = df['MYOPIA_CLASS'].value_counts().sort_index()
    for cid, count in dist.items():
        pct = (count / len(df)) * 100
        print(f"          * {config.CLASS_NAMES[cid]} (Classe {cid}): {count} ({pct:.2f}%)")

def print_cycle_volumetry(df):
    print(f"       -> Volumetria por ciclo:")
    for cycle_name, count in df['CYCLE_YEAR'].value_counts().sort_index().items():
        pct = (count / len(df)) * 100
        print(f"          * {cycle_name}: {count} registros ({pct:.2f}%)")

def save_dataframe(df, output_file):
    df.to_csv(output_file, index=False)
    print(f"\n[OK] Base salva com sucesso em: '{output_file}'")