import os
import urllib.request
import pandas as pd
import numpy as np

# Configurações de URLs oficiais do CDC - NHANES Ciclo 2005-2006 (Ciclo D)
NHANES_URLS = {
    "demographics": "https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/DEMO_D.XPT",
    "vision_exam": "https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/VIX_D.XPT",
    "body_measures": "https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/BMX_D.XPT",
    #"vitamin_d": "https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/VID_D.XPT"
}

def download_file(url, dest_folder="app/src/data"):
    """Faz o download do arquivo XPT se ele não existir localmente."""
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    filename = url.split("/")[-1]
    filepath = os.path.join(dest_folder, filename)
    
    if os.path.exists(filepath):
        print(f"[*] Arquivo {filename} já existe localmente. Pulando download.")
    else:
        print(f"[+] Baixando {filename} de {url}...")
        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"[✔] Download de {filename} concluído com sucesso!")
        except Exception as e:
            print(f"[❌] Erro ao baixar {filename}: {e}")
            print("Verifique sua conexão com a internet ou se o link do CDC NHANES mudou.")
            
    return filepath

def load_and_preprocess_nhanes(raw_dir="app/src/data", output_path="nhanes_myopia_cleaned.csv"):
    """
    Carrega as tabelas baixadas do NHANES 2005-2006, mescla os dados
    e faz a limpeza de dados e engenharia de recursos (features).
    """
    print("\n--- Iniciando Processamento de Dados NHANES ---")
    
    # Caminhos locais
    demo_path = os.path.join(raw_dir, "DEMO_D.XPT")
    vix_path = os.path.join(raw_dir, "VIX_D.XPT")
    bmx_path = os.path.join(raw_dir, "BMX_D.XPT")
    vid_path = os.path.join(raw_dir, "VID_D.XPT")
    
    # Validando se os arquivos existem
    for path in [demo_path, vix_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Arquivo obrigatório {path} não encontrado! Execute a etapa de download primeiro."
            )
            
    # 1. Carregando dados Demográficos (DEMO_D)
    print("[1/5] Carregando dados Demográficos...")
    df_demo = pd.read_sas(demo_path, format="xport")
    # Colunas de Interesse: 
    # SEQN (ID), RIAGENDR (Gênero: 1=Masc, 2=Fem), RIDAGEYR (Idade em anos), 
    # RIDRETH1 (Etnia), INDFMPIR (Razão Renda Familiar/Pobreza)
    cols_demo = ["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH1", "INDFMPIR"]
    df_demo = df_demo[cols_demo].copy()
    
    # Codificação amigável para Demografia
    df_demo["RIAGENDR"] = df_demo["RIAGENDR"].map({1: "Masculino", 2: "Feminino"})
    
    # 2. Carregando dados de Exame de Visão (VIX_D)
    print("[2/5] Carregando dados de Exames Oficiais de Visão...")
    df_vix = pd.read_sas(vix_path, format="xport")
    # Variáveis de refração automatizada:
    # VIASPHR (Esfera Olho Direito), VIACYLR (Cilindro Olho Direito)
    # VIASPHL (Esfera Olho Esquerdo), VIACYLL (Cilindro Olho Esquerdo)
    # VIXEXR/VIXEXL (Status do exame: 1=Completo, etc.)
    cols_vix = ["SEQN", "VIASPHR", "VIACYLR", "VIASPHL", "VIACYLL", "VIXEXR", "VIXEXL"]
    df_vix = df_vix[cols_vix].copy()
    
    # Filtrar apenas participantes que possuem alguma medição de refração (evitar linhas totalmente vazias)
    df_vix = df_vix.dropna(subset=["VIASPHR", "VIASPHL"], how="all")
    
    # 3. Engenharia de Recursos (Target e Metadados Clínicos)
    print("[3/5] Calculando o Equivalente Esférico (SE)...")
    # Equivalente Esférico (SE) = Esfera + (Cilindro / 2)
    df_vix["SE_RIGHT"] = df_vix["VIASPHR"] + (df_vix["VIACYLR"] / 2.0)
    df_vix["SE_LEFT"] = df_vix["VIASPHL"] + (df_vix["VIACYLL"] / 2.0)
    
    # Para consistência do diagnóstico, usaremos a média de ambos os olhos ou o olho disponível
    df_vix["SE_MEAN"] = df_vix[["SE_RIGHT", "SE_LEFT"]].mean(axis=1)
    
    # Rotulagem para o problema de CLASSIFICAÇÃO de Miopia
    # Convenção Clínica: 
    # - Sem Miopia (SE > -0.5 D)
    # - Miopia Leve/Moderada (-6.0 D < SE <= -0.5 D)
    # - Alta Miopia (SE <= -6.0 D)
    def classificar_miopia(se):
        if pd.isna(se):
            return np.nan
        elif se <= -6.0:
            return 2  # Alta Miopia
        elif se <= -0.5:
            return 1  # Miopia Leve/Moderada
        else:
            return 0  # Sem Miopia (Emétrope/Hipermetrope)
            
    df_vix["MYOPIA_CLASS"] = df_vix["SE_MEAN"].apply(classificar_miopia)
    
    # 4. Carregando dados adicionais opcionais (BMI e Vitamina D) se disponíveis
    # Mesclar dados de composição corporal (BMX_D)
    if os.path.exists(bmx_path):
        print("[+] Mesclando dados antropométricos (IMC)...")
        df_bmx = pd.read_sas(bmx_path, format="xport")[["SEQN", "BMXWT", "BMXHT", "BMXBMI"]]
        df_demo = pd.merge(df_demo, df_bmx, on="SEQN", how="left")
        
    # Mesclar dados laboratoriais de Vitamina D (VID_D)
    if os.path.exists(vid_path):
        print("[+] Mesclando dados laboratoriais de Vitamina D...")
        # LBDVIDMS (Concentração de Vitamina D em nmol/L)
        df_vid = pd.read_sas(vid_path, format="xport")[["SEQN", "LBDVIDMS"]]
        df_demo = pd.merge(df_demo, df_vid, on="SEQN", how="left")
        
    # 5. Mesclagem Final (Merge) das Bases
    print("[4/5] Realizando a mesclagem final das tabelas...")
    final_df = pd.merge(df_vix, df_demo, on="SEQN", how="inner")
    
    # Removendo linhas onde a classe alvo (MYOPIA_CLASS) é nula
    final_df = final_df.dropna(subset=["MYOPIA_CLASS"])
    
    # Salvando a base limpa e estruturada
    print(f"[5/5] Exportando base tratada para {output_path}...")
    final_df.to_csv(output_path, index=False)
    print(f"[✔] Processamento concluído! Registros finais: {len(final_df)}")
    
    return final_df

if __name__ == "__main__":
    # 1. Download dos arquivos de dados brutos
    print("=== ETAPA 1: Download de Arquivos NHANES do CDC ===")
    local_files = {}
    for key, url in NHANES_URLS.items():
        local_files[key] = download_file(url, dest_folder="app/src/data")
        
    # 2. Processamento das Tabelas e Junção Baseada em SEQN
    print("\n=== ETAPA 2: Processamento e Limpeza ===")
    try:
        df_limpo = load_and_preprocess_nhanes(raw_dir="app/src/data", output_path="nhanes_myopia_cleaned.csv")
        print("\n[✔] Pipeline executada com sucesso!")
        print(df_limpo.head())
    except FileNotFoundError as e:
        print(f"\n[❌] Erro de arquivo: {e}")
        print("Certifique-se de executar este script em um ambiente local com acesso à internet.")
