"""
EXEMPLO SIMPLES: Processar Múltiplos Ficheiros

Este script processa vários ficheiros .dat de forma automática.
Ajusta os parâmetros abaixo conforme necessário.
"""

from batch_analysis import BatchAnalyzer

# =============================================================================
# CONFIGURAÇÃO (AJUSTA AQUI!)
# =============================================================================

# Diretório com os ficheiros .dat
DATA_DIR = 'uploads'

# Diretório para salvar resultados
OUTPUT_DIR = 'outputs'

# Número de ficheiros a processar (None = todos)
MAX_FILES = 10  # ⬅️ COMEÇA COM POUCOS!

# Padrão de ficheiros (ex: '*.dat', '*m0.dat', 's0*.dat')
PATTERN = '*.dat'

# Métodos a executar
# Opções: 'bb' (Branch&Bound), 'sa' (SimAnnealing), 'tabu', 'hybrid'
METHODS = ['bb', 'sa', 'hybrid']  # Recomendado: exclui Tabu (lento)

# Pesos dos objetivos
LAMBDA1 = 0.5  # Peso do custo operacional (0-1)
LAMBDA2 = 0.5  # Peso do equilíbrio de carga (0-1)

# Tempo limite por método (segundos)
TIME_LIMIT = 120  # 2 minutos

# =============================================================================
# NÃO MEXER ABAIXO (a menos que saibas o que estás a fazer)
# =============================================================================

def main():
    print("="*80)
    print("PROCESSAMENTO EM BATCH - ALOCAÇÃO DE PACIENTES")
    print("="*80)
    print(f"\n📁 Diretório de dados: {DATA_DIR}")
    print(f"📁 Diretório de outputs: {OUTPUT_DIR}")
    print(f"📊 Padrão de ficheiros: {PATTERN}")
    print(f"🔢 Máximo de ficheiros: {MAX_FILES if MAX_FILES else 'TODOS'}")
    print(f"⚙️  Métodos: {METHODS}")
    print(f"⏱️  Tempo limite: {TIME_LIMIT}s por método")
    print(f"⚖️  Pesos: λ1={LAMBDA1}, λ2={LAMBDA2}")
    
    resposta = input("\n▶️  Continuar? (s/n): ")
    
    if resposta.lower() != 's':
        print("❌ Cancelado pelo utilizador.")
        return
    
    # Criar analisador
    analyzer = BatchAnalyzer(DATA_DIR, OUTPUT_DIR)
    
    # Executar análise
    analyzer.run_batch_analysis(
        pattern=PATTERN,
        max_files=MAX_FILES,
        methods=METHODS,
        lambda1=LAMBDA1,
        lambda2=LAMBDA2,
        time_limit=TIME_LIMIT
    )
    
    print("\n" + "="*80)
    print("✅ CONCLUÍDO!")
    print("="*80)
    print(f"\nResultados salvos em: {OUTPUT_DIR}/")
    print("\nFicheiros gerados:")
    print("  • batch_results.csv       - Tabela com todos os resultados")
    print("  • batch_comparison.png    - Gráficos comparativos")
    print("  • scalability.png         - Análise de escalabilidade")
    print("  • batch_report.txt        - Relatório detalhado")
    print("\n💡 Dica: Abre batch_results.csv no Excel para análise detalhada!")
    print()


if __name__ == "__main__":
    main()
