import os
import pandas as pd
import config

def cycle_dir(cycle):
    return os.path.join(config.NHANES_DIR, cycle["name"])

def resolve_xpt_path(cycle, component):
    """Resolve o caminho do .XPT de um componente do ciclo, tolerando a extensão
    em maiúsculas ou minúsculas. Retorna None quando o arquivo não existe."""
    for extension in ("XPT", "xpt"):
        path = os.path.join(cycle_dir(cycle), f"{component}{cycle['suffix']}.{extension}")
        if os.path.exists(path):
            return path
    return None

def _read_sas(cycle, component):
    path = resolve_xpt_path(cycle, component)
    if path is None:
        raise FileNotFoundError(f"{component}{cycle['suffix']}.XPT não encontrado em '{cycle_dir(cycle)}'")
    df = pd.read_sas(path, format="xport")
    # Normaliza as colunas para maiúsculas para evitar disparidades entre ciclos (ex: seqn vs SEQN)
    df.columns = df.columns.str.upper()
    return df

def check_cycle_files(cycle):
    """Verifica se os componentes fundamentais do ciclo estão disponíveis para o merge."""
    missing = [c for c in config.REQUIRED_COMPONENTS if resolve_xpt_path(cycle, c) is None]
    if missing:
        print(f"       [-] Arquivos {missing} ausentes em '{cycle_dir(cycle)}'. Pulando ciclo.")
        return False
    return True

def load_demographic_data(cycle):
    print(f"[1/4] Carregando dados demográficos {cycle['name']} (DEMO{cycle['suffix']}.XPT)...")
    df = _read_sas(cycle, "DEMO")
    df = df[[col for col in config.DEMO_COLS if col in df.columns]].copy()
    print(f"       -> {len(df)} registros carregados.")
    return df

def load_vision_data(cycle):
    print(f"[2/4] Carregando dados do exame de visão {cycle['name']} (VIX{cycle['suffix']}.XPT)...")
    df = _read_sas(cycle, "VIX")
    
    missing_target = [col for col in config.VIX_TARGET_COLS if col not in df.columns]
    if missing_target:
        print(f"       [-] Ciclo sem colunas refrativas essenciais: {missing_target}. Pulando ciclo.")
        return None

    available_optional = [col for col in config.VIX_OPTIONAL_COLS if col in df.columns]
    df = df[config.VIX_TARGET_COLS + available_optional].copy()

    print(f"       -> {len(df)} registros carregados.")
    return df

def load_anthropometric_data(cycle):
    print(f"[3/4] Carregando dados antropométricos {cycle['name']} (BMX{cycle['suffix']}.XPT)...")
    df = _read_sas(cycle, "BMX")
    selected_cols = [col for col in config.BMX_COLS if col in df.columns]
    df = df[selected_cols].copy()
    print(f"       -> {len(df)} registros carregados.")
    return df

def load_vitamin_d_data(cycle):
    print(f"[4/4] Carregando dados de laboratório de Vitamina D {cycle['name']} (VID{cycle['suffix']}.XPT)...")
    try:
        df_raw = _read_sas(cycle, "VID")
    except Exception as e:
        print(f"       [!] Nota: Não foi possível processar VID{cycle['suffix']}.XPT ({e}). O pipeline continuará sem os níveis séricos de Vitamina D.")
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