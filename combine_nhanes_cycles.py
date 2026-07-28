# -*- coding: utf-8 -*-
"""
Script de Harmonização e Consolidação de Ciclos Históricos do NHANES (1999-2008)
Desenvolvido para o projeto TCC: Inteligência Artificial para Diagnóstico de Miopia.

Este script lê os dados brutos (.XPT) dos ciclos:
- 1999-2000 (Sem sufixo)
- 2001-2002 (_B)
- 2003-2004 (_C)
- 2005-2006 (_D)
- 2007-2008 (_E)

Aplica regras de higienização de anomalias (código 88), harmoniza o top-coding
de idade (corte em 80 anos), calcula o Equivalente Esférico (SE) e gera
uma base de dados unificada de alta volumetria para o treinamento dos modelos.
"""

import os
import pandas as pd
import numpy as np

def process_cycle(raw_dir, suffix, cycle_name):
    """
    Processa e harmoniza os dados de um único ciclo do NHANES.
    
    Parâmetros:
    -----------
    raw_dir : str
        Diretório contendo os arquivos .XPT brutos.
    suffix : str
        Sufixo do arquivo correspondente ao ciclo (ex: '', '_B', '_C', '_D', '_E').
    cycle_name : str
        Nome amigável do ciclo de dados (ex: '1999-2000').
        
    Retorna:
    --------
    pd.DataFrame ou None
        DataFrame processado ou None se arquivos estiverem ausentes.
    """
    # Define os nomes dos arquivos com base no sufixo do ciclo
    demo_file = f"DEMO{suffix}.XPT"
    bmx_file = f"BMX{suffix}.XPT"
    vix_file = f"VIX{suffix}.XPT"

    demo_path = os.path.join(raw_dir, demo_file)
    bmx_path = os.path.join(raw_dir, bmx_file)
    vix_path = os.path.join(raw_dir, vix_file)

    # Verifica se os três arquivos fundamentais estão disponíveis para o merge
    if not (os.path.exists(demo_path) and os.path.exists(bmx_path) and os.path.exists(vix_path)):
        print(f"[-] Arquivos para o ciclo {cycle_name} ({suffix}) incompletos no diretório '{raw_dir}'. Pulando ciclo.")
        return None

    print(f"[+] Processando ciclo {cycle_name} ({demo_file}, {bmx_file}, {vix_file})...")

    # Leitura dos arquivos binários do SAS (XPORT)
    try:
        df_demo = pd.read_sas(demo_path, format="xport")
        df_bmx = pd.read_sas(bmx_path, format="xport")
        df_vix = pd.read_sas(vix_path, format="xport")
    except Exception as e:
        print(f"[!] Erro ao ler arquivos SAS para o ciclo {cycle_name}: {e}")
        return None

    # Normalizar as colunas para maiúsculas para evitar disparidades (ex: seqn vs SEQN)
    df_demo.columns = df_demo.columns.str.upper()
    df_bmx.columns = df_bmx.columns.str.upper()
    df_vix.columns = df_vix.columns.str.upper()

    # --- 1. PROCESSAR DEMOGRAFIA (DEMO) ---
    # Variáveis de interesse: SEQN (ID), RIAGENDR (Gênero), RIDAGEYR (Idade), RIDRETH1 (Raça), INDFMPIR (Pobreza/Renda)
    demo_cols = ['SEQN', 'RIAGENDR', 'RIDAGEYR', 'RIDRETH1', 'INDFMPIR']
    df_demo_filtered = df_demo[[c for c in demo_cols if c in df_demo.columns]].copy()

    # HARMONIZAÇÃO CRÍTICA DA IDADE (Top-Coding):
    # Nos ciclos de 1999 a 2006, o limite de idade (top-code) foi fixado em 85 anos.
    # No ciclo 2007-2008, o limite foi reduzido para 80 anos.
    # Para evitar anomalias na curva de idade do modelo de IA, aplicamos um corte uniforme em 80 anos.
    if 'RIDAGEYR' in df_demo_filtered.columns:
        df_demo_filtered['RIDAGEYR'] = df_demo_filtered['RIDAGEYR'].clip(upper=80)

    # --- 2. PROCESSAR ANTROPOMETRIA (BMX) ---
    # Variáveis de interesse: SEQN, BMXWT (Peso), BMXHT (Altura), BMXBMI (IMC), BMXWAIST (Circunferência Cintura)
    bmx_cols = ['SEQN', 'BMXWT', 'BMXHT', 'BMXBMI', 'BMXWAIST']
    df_bmx_filtered = df_bmx[[c for c in bmx_cols if c in df_bmx.columns]].copy()

    # --- 3. PROCESSAR EXAME DE VISÃO (VIX) ---
    # Colunas essenciais da refração objetiva
    vix_cols = ['SEQN', 'VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']
    
    # Validação de integridade do exame refrativo
    missing_cols = [c for c in vix_cols if c not in df_vix.columns]
    if missing_cols:
        print(f"[-] Ciclo {cycle_name} não possui colunas refrativas essenciais: {missing_cols}. Pulando.")
        return None

    df_vix_filtered = df_vix[vix_cols].copy()

    # HIGIENIZAÇÃO DE ANOMALIAS (Código 88):
    # No banco de dados do NHANES, o valor 88.00 ou 888.00 indica "Could not obtain" (Não pôde ser obtido).
    # Se não substituído por NaN, a IA interpretará que o paciente tem +88 graus de miopia/astigmatismo!
    # Esferas e Cilindros (Códigos 88 e 88.0)
    for col in ['VIXORSM', 'VIXORCM', 'VIXOLSM', 'VIXOLCM']:
        df_vix_filtered[col] = df_vix_filtered[col].replace([88.0, 88.00], np.nan)
    # Eixos de Astigmatismo (Códigos 888 e 888.0)
    for col in ['VIXORAM', 'VIXOLAM']:
        df_vix_filtered[col] = df_vix_filtered[col].replace([888.0, 888.00], np.nan)

    # --- 4. MERGE E CONSOLIDAÇÃO DAS TRÊS FONTES ---
    # Fusão usando ID único do paciente (SEQN)
    df_merged = df_demo_filtered.merge(df_bmx_filtered, on='SEQN', how='inner')
    df_merged = df_merged.merge(df_vix_filtered, on='SEQN', how='inner')

    # --- 5. CÁLCULOS CLÍNICOS E DO ALVO (TARGET) ---
    # Equivalente Esférico (SE) = Esfera + (Cilindro / 2)
    # Calculado individualmente para o olho direito (RIGHT) e esquerdo (LEFT)
    df_merged['SE_RIGHT'] = df_merged['VIXORSM'] + (df_merged['VIXORCM'] / 2.0)
    df_merged['SE_LEFT'] = df_merged['VIXOLSM'] + (df_merged['VIXOLCM'] / 2.0)

    # Equivalente Esférico Consolidado (Média Refrativa Binocular)
    df_merged['SE_MEAN'] = df_merged[['SE_RIGHT', 'SE_LEFT']].mean(axis=1)

    # Excluir linhas onde não foi possível calcular o Equivalente Esférico de nenhum dos olhos
    df_merged = df_merged.dropna(subset=['SE_MEAN'])

    # --- 6. ROTULAGEM DAS CLASSES DE MIOPIA (ABNT / Diretrizes Clínicas) ---
    # Classe 0: Sem Miopia (SE_MEAN > -0.50 dioptrias)
    # Classe 1: Miopia Leve a Moderada (-6.00 <= SE_MEAN <= -0.50 dioptrias)
    # Classe 2: Alta Miopia (SE_MEAN < -6.00 dioptrias)
    df_merged['MYOPIA_CLASS'] = 0
    df_merged.loc[(df_merged['SE_MEAN'] <= -0.50) & (df_merged['SE_MEAN'] >= -6.00), 'MYOPIA_CLASS'] = 1
    df_merged.loc[df_merged['SE_MEAN'] < -6.00, 'MYOPIA_CLASS'] = 2

    # Registra a origem histórica para análises de coorte ou estratificação
    df_merged['CYCLE_YEAR'] = cycle_name

    return df_merged

def combine_all_nhanes_cycles(raw_dir="raw_data", output_path="nhanes_myopia_combined.csv"):
    """
    Função principal que gerencia o fluxo de leitura, tratamento e consolidação
    dos 5 ciclos de dados históricos do NHANES.
    """
    # Mapeamento do ciclo para o sufixo de arquivo padrão do CDC
    cycles = [
        {"suffix": "", "name": "1999-2000"},
        {"suffix": "_B", "name": "2001-2002"},
        {"suffix": "_C", "name": "2003-2004"},
        {"suffix": "_D", "name": "2005-2006"},
        {"suffix": "_E", "name": "2007-2008"},
    ]

    processed_dfs = []

    print("=== INICIANDO HARMONIZAÇÃO HISTÓRICA DO NHANES (1999-2008) ===")
    
    for cycle in cycles:
        df_cycle = process_cycle(raw_dir, cycle["suffix"], cycle["name"])
        if df_cycle is not None:
            processed_dfs.append(df_cycle)

    if not processed_dfs:
        print("[!] Erro: Nenhum ciclo de dados foi carregado. Verifique os caminhos e tente novamente.")
        return None

    # Concatenar todos os DataFrames consolidados em uma única base unificada
    df_combined = pd.concat(processed_dfs, ignore_index=True)

    # Tratamento de valores ausentes (Imputação de variáveis socioeconômicas/antropométricas se nulas)
    # Para o modelo preditivo final, as variáveis como INDFMPIR ou BMXWAIST podem conter alguns NaNs que o scikit-learn
    # ou XGBoost podem tratar, mas garantimos que a integridade estrutural básica seja preservada.

    # Salva a base combinada higienizada
    try:
        df_combined.to_csv(output_path, index=False)
        print(f"\n[✔] CONSOLIDAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"|--- Base exportada em: '{output_path}'")
        print(f"|--- Volumetria total unificada: {df_combined.shape[0]} registros de pacientes.")
        print(f"|--- Dimensões da matriz de dados: {df_combined.shape[1]} colunas mapeadas.")
        print("|")
        print("|--- Distribuição das Classes de Miopia na Base de IA Combinada:")
        counts = df_combined['MYOPIA_CLASS'].value_counts()
        total = len(df_combined)
        for cls, count in counts.items():
            desc = "Sem Miopia" if cls == 0 else "Miopia Leve/Mod" if cls == 1 else "Alta Miopia"
            pct = (count / total) * 100
            print(f"|     - Classe {cls} ({desc}): {count} registros ({pct:.2f}%)")
        print("=================================================================")
    except Exception as e:
        print(f"[!] Erro ao salvar arquivo consolidado CSV: {e}")

    return df_combined

if __name__ == "__main__":
    # Caso executado diretamente, procura a pasta padrão 'raw_data' e gera a saída combinada
    # Criar pasta raw_data se não existir (apenas segurança de caminhos)
    if not os.path.exists("raw_data"):
        os.makedirs("raw_data")
        print("[i] Pasta 'raw_data' criada automaticamente. Adicione seus arquivos .XPT nela.")
    
    # Executa a fusão
    combine_all_nhanes_cycles(raw_dir="raw_data", output_path="nhanes_myopia_combined.csv")
