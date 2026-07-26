import os
import sys
import urllib.request
import pandas as pd
import numpy as np

# Configurações do script
RAW_DIR = "app/src/data/NHANES"
OUTPUT_FILE = "app/src/data/data_cleaned/nhanes_myopia_cleaned.csv"

def show_manual_instructions():
    """Exibe instruções claras de como o usuário pode baixar os arquivos caso haja bloqueio."""
    print("\n" + "="*70)
    print("⚠️  BLOQUEIO DE DOWNLOAD DETECTADO (SISTEMA DE SEGURANÇA DO CDC)")
    print("="*70)
    print("Para continuar seu projeto de TCC sem problemas, siga este passo a passo rápido:")
    print("1. Crie uma pasta chamada 'app/src/data/NHANES' no mesmo diretório deste script.")
    print("2. Abra os seguintes links no seu navegador e salve os arquivos dentro da pasta 'app/src/data/NHANES':")
    for filename, url in URLS.items():
        print(f"   • Link: {url}")
        print(f"     Salvar como: {filename}\n")
    print("3. Após colocar os 4 arquivos na pasta 'app/src/data/NHANES', execute este script novamente.")
    print("O script detectará os arquivos locais e fará todo o processamento automaticamente.")
    print("="*70 + "\n")

def process_data():
    """Carrega os arquivos binários do SAS (.XPT) locais e realiza o processamento higiênico."""
    print("\n=== ETAPA 2: Processamento e Higienização dos Dados ===")
    
    # 1. Carregando dados demográficos
    demo_path = os.path.join(RAW_DIR, "DEMO_D.XPT")
    print("[1/4] Carregando dados demográficos (DEMO_D.XPT)...")
    try:
        df_demo = pd.read_sas(demo_path, format="xport")
        # Manter variáveis de interesse: SEQN (ID), Idade, Sexo, Etnia, Relação de Renda Familiar
        df_demo = df_demo[['SEQN', 'RIDAGEYR', 'RIAGENDR', 'RIDRETH1', 'INDFMPIR']].copy()
        print(f"      -> {len(df_demo)} registros carregados.")
    except Exception as e:
        print(f"[❌] Erro ao ler DEMO_D.XPT: {e}")
        return

    # 2. Carregando dados do exame de visão (VIX_D.XPT)
    vix_path = os.path.join(RAW_DIR, "VIX_D.XPT")
    print("[2/4] Carregando dados do exame de visão (VIX_D.XPT)...")
    try:
        df_vix = pd.read_sas(vix_path, format="xport")
        
        # Colunas corretas para refração objetiva em 2005-2006:
        # VIXORSM: Esfera Olho Direito (median value of three objective refractions)
        # VIXORCM: Cilindro Olho Direito (median value of three objective refractions)
        # VIXOLSM: Esfera Olho Esquerdo (median value of three objective refractions)
        # VIXOLCM: Cilindro Olho Esquerdo (median value of three objective refractions)
        
        target_cols = ['SEQN', 'VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']
        
        # Opcional: Adicionar variáveis de acuidade visual ou ceratometria se quiser enriquecer
        additional_cols = ['VIDRVA', 'VIDLVA', 'VIXKRMM', 'VIXKLMM']
        available_additional = [col for col in additional_cols if col in df_vix.columns]
        
        df_vix = df_vix[target_cols + available_additional].copy()
        print(f"      -> {len(df_vix)} registros carregados.")
    except Exception as e:
        print(f"[❌] Erro ao ler VIX_D.XPT: {e}")
        return

    # 3. Carregando dados antropométricos (BMX_D.XPT)
    bmx_path = os.path.join(RAW_DIR, "BMX_D.XPT")
    print("[3/4] Carregando dados antropométricos (BMX_D.XPT)...")
    try:
        df_bmx = pd.read_sas(bmx_path, format="xport")
        # BMXWT (Peso), BMXHT (Altura), BMXBMI (IMC), BMXWAIST (Circunferência da Cintura)
        bmx_cols = ['SEQN', 'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST']
        df_bmx = df_bmx[[col for col in bmx_cols if col in df_bmx.columns]].copy()
        print(f"      -> {len(df_bmx)} registros carregados.")
    except Exception as e:
        print(f"[❌] Erro ao ler BMX_D.XPT: {e}")
        return

    # 4. Carregando dados de laboratório de Vitamina D (VID_D.XPT)
    vid_path = os.path.join(RAW_DIR, "VID_D.XPT")
    print("[4/4] Carregando dados de laboratório de Vitamina D (VID_D.XPT)...")
    has_vit_d = False
    df_vid = pd.DataFrame()
    try:
        df_vid_raw = pd.read_sas(vid_path, format="xport")
        
        # Identificar dinamicamente o nome da coluna de Vitamina D sérica (25-hydroxyvitamin D)
        # No ciclo 2005-2006, é comumente LBDVIDMS ou LBXVIDMS (concentração em nmol/L ou ng/mL)
        vit_d_candidates = ['LBDVIDMS', 'LBXVIDMS', 'LBDVID', 'LBXVID']
        vit_d_col = None
        for candidate in vit_d_candidates:
            if candidate in df_vid_raw.columns:
                vit_d_col = candidate
                break
        
        if vit_d_col:
            df_vid = df_vid_raw[['SEQN', vit_d_col]].copy()
            df_vid.rename(columns={vit_d_col: 'VITAMIN_D_LEVEL'}, inplace=True)
            has_vit_d = True
            print(f"      -> {len(df_vid)} registros carregados (usando coluna '{vit_d_col}').")
        else:
            print("      [!] Coluna de Vitamina D não identificada de forma padrão. Continuando sem Vitamina D sérica.")
    except Exception as e:
        print(f"      [!] Nota: Não foi possível processar VID_D.XPT ({e}). O pipeline continuará sem os níveis séricos de Vitamina D.")

    # === PROCESSAMENTO DE VALORES AUSENTES E CLÍNICOS ===
    print("\n--- Processando Refração e Calculando Equivalente Esférico ---")
    
    # Tratando códigos de erro específicos do NHANES na refração objetiva
    # O valor 88 ou 888 representa "Could not obtain" (Não foi possível obter) na refração e deve ser convertido para NaN.
    for col in ['VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']:
        df_vix.loc[df_vix[col] == 88, col] = np.nan
        df_vix.loc[df_vix[col] == 888, col] = np.nan

    # Cálculo do Equivalente Esférico (SE = Esfera + Cilindro / 2) para cada olho
    df_vix['SE_RIGHT'] = df_vix['VIXORSM'] + (df_vix['VIXORCM'] / 2.0)
    df_vix['SE_LEFT'] = df_vix['VIXOLSM'] + (df_vix['VIXOLCM'] / 2.0)

    # Definir Equivalente Esférico Médio (se um olho estiver ausente, usa o outro. Se ambos ausentes, vira NaN)
    df_vix['SE_MEAN'] = df_vix[['SE_RIGHT', 'SE_LEFT']].mean(axis=1)

    # Filtrar apenas participantes que possuem um Equivalente Esférico válido (nossa variável base)
    df_vix_filtered = df_vix.dropna(subset=['SE_MEAN']).copy()
    print(f"      -> {len(df_vix) - len(df_vix_filtered)} participantes removidos por não realizarem o exame refrativo.")
    print(f"      -> Restaram {len(df_vix_filtered)} registros válidos com exames de visão.")

    # Classificação Clínica da Severidade da Miopia baseada nas diretrizes do NHANES/Estudos Coreanos:
    # Classe 0: Sem miopia (SE > -0.5 dioptrias)
    # Classe 1: Miopia Leve/Moderada (-6.0 <= SE <= -0.5 dioptrias)
    # Classe 2: Alta Miopia (SE < -6.0 dioptrias)
    def classificar_miopia(se):
        if se > -0.5:
            return 0  # Sem Miopia / Emétrope ou Hipermetrope
        elif se >= -6.0:
            return 1  # Miopia Leve/Moderada
        else:
            return 2  # Alta Miopia

    df_vix_filtered['MYOPIA_CLASS'] = df_vix_filtered['SE_MEAN'].apply(classificar_miopia)

    # === MESCLAR TODAS AS FONTES (MERGE POR SEQN) ===
    print("\n--- Mesclando tabelas (Merge por ID do participante)... ---")
    
    # Inicia o dataframe consolidado com os exames de visão filtrados
    df_consolidado = df_vix_filtered

    # Merge com Demografia
    df_consolidado = pd.merge(df_consolidado, df_demo, on='SEQN', how='inner')
    
    # Merge com Antropometria
    df_consolidado = pd.merge(df_consolidado, df_bmx, on='SEQN', how='left')
    
    # Merge com Vitamina D (se disponível)
    if has_vit_d:
        df_consolidado = pd.merge(df_consolidado, df_vid, on='SEQN', how='left')

    # Garantir codificações de dados de forma intuitiva
    # Sexo no NHANES: 1 = Masculino, 2 = Feminino. Vamos renomear a coluna e converter para 0 (M) e 1 (F)
    df_consolidado['IS_FEMALE'] = (df_consolidado['RIAGENDR'] == 2).astype(int)
    df_consolidado.drop(columns=['RIAGENDR'], inplace=True)
    
    # Renomear variáveis demográficas para nomes mais legíveis no seu TCC
    df_consolidado.rename(columns={
        'RIDAGEYR': 'AGE',
        'RIDRETH1': 'ETHNICITY',
        'INDFMPIR': 'INCOME_PIR',
        'BMXWT': 'WEIGHT_KG',
        'BMXHT': 'HEIGHT_CM',
        'BMXBMI': 'BMI',
        'BMXWAIST': 'WAIST_CIRC_CM'
    }, inplace=True)

    print(f"\n[✔] Consolidação Concluída!")
    print(f"      -> Total de instâncias: {len(df_consolidado)}")
    print(f"      -> Distribuição das classes de miopia:")
    dist = df_consolidado['MYOPIA_CLASS'].value_counts()
    classes_nomes = {0: "Sem Miopia", 1: "Miopia Leve/Moderada", 2: "Alta Miopia"}
    for cid, count in dist.items():
        pct = (count / len(df_consolidado)) * 100
        print(f"         * {classes_nomes[cid]} (Classe {cid}): {count} ({pct:.2f}%)")

    # Salvar base limpa
    df_consolidado.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[💾] Base consolidada salva com sucesso em: '{OUTPUT_FILE}'")
    print("Tudo pronto para iniciar a análise exploratória de dados (EDA) e treinamento dos modelos!")

def main():
    print("="*60)
    print("  NHANES 2005-2006 Vision Data Processor (v3 - Corrigido)")
    print("="*60)

    # Garante que a pasta de destino exista
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)

    all_ok = True

    # Se faltar algum arquivo, mostra instruções manuais e para
    if not all_ok:
        # Verifica se pelo menos já existem localmente
        locais_ok = True
        for filename in URLS.keys():
            if not os.path.exists(os.path.join(RAW_DIR, filename)):
                locais_ok = False
        
        if not locais_ok:
            show_manual_instructions()
            sys.exit(1)
        else:
            print("[i] Alguns downloads falharam, mas os arquivos locais correspondentes foram encontrados!")

    # Executa o processamento
    process_data()

if __name__ == "__main__":
    main()
