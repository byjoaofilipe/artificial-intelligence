# 📦 GUIA: PROCESSAR MÚLTIPLOS FICHEIROS .DAT

## 🎯 Objetivo

Este guia explica como processar **centenas ou milhares** de ficheiros .dat automaticamente usando o script `batch_analysis.py`.

---

## ✅ PREPARAÇÃO

### 1. Estrutura dos Dados

Coloca todos os ficheiros `.dat` numa pasta, por exemplo:

```
/uploads/
├── s0m0.dat
├── s0m1.dat
├── s0m2.dat
├── ...
└── s999m3.dat
```

### 2. Instalar Dependências

```bash
pip install gurobipy matplotlib pandas numpy
```

---

## 🚀 COMO USAR

### Opção 1: Teste Rápido (5-10 ficheiros) ⭐ RECOMENDADO

```python
from batch_analysis import BatchAnalyzer

# Criar analisador
analyzer = BatchAnalyzer(
    data_directory='/uploads',
    output_directory='/outputs'
)

# Processar apenas 10 ficheiros para teste
analyzer.run_batch_analysis(
    pattern='*.dat',
    max_files=10,           # Apenas 10 ficheiros
    methods=['bb', 'sa', 'hybrid'],  # Excluir Tabu (é lento)
    lambda1=0.5,
    lambda2=0.5,
    time_limit=120          # 2 minutos por método
)
```

**Tempo estimado**: ~5-10 minutos para 10 ficheiros

---

### Opção 2: Filtrar por Padrão

```python
# Processar apenas ficheiros com M=0
analyzer.run_batch_analysis(
    pattern='*m0.dat',      # Apenas ficheiros que terminam em m0.dat
    max_files=None,         # Todos os que correspondem ao padrão
    methods=['bb', 'sa', 'hybrid'],
    lambda1=0.5,
    lambda2=0.5,
    time_limit=120
)
```

**Padrões úteis**:
- `'s0*.dat'` - Todos os ficheiros que começam com s0
- `'*m0.dat'` - Todos com M=0
- `'*m1.dat'` - Todos com M=1
- `'*.dat'` - TODOS os ficheiros

---

### Opção 3: Processar TODOS os 1000 Ficheiros ⚠️

```python
analyzer.run_batch_analysis(
    pattern='*.dat',
    max_files=None,         # SEM LIMITE!
    methods=['bb', 'sa', 'hybrid'],
    lambda1=0.5,
    lambda2=0.5,
    time_limit=300          # 5 minutos por método
)
```

**⚠️ ATENÇÃO**:
- Tempo estimado: **5-20 HORAS** (depende do hardware)
- Recomenda-se executar de noite ou em servidor
- Deixa a correr e vai fazer outra coisa!

---

## ⚙️ CONFIGURAÇÕES

### Escolher Métodos

```python
methods=['bb', 'sa', 'hybrid']  # Recomendado (rápido + completo)
methods=['bb']                   # Apenas Branch & Bound
methods=['sa', 'tabu']           # Apenas metaheurísticas
methods=['bb', 'sa', 'tabu', 'hybrid']  # TODOS (lento!)
```

**Recomendação**: 
- **Testes**: `['bb', 'sa', 'hybrid']` (exclui Tabu que é lento)
- **Análise completa**: `['bb', 'sa', 'tabu', 'hybrid']`

### Ajustar Tempo Limite

```python
time_limit=60    # 1 minuto (rápido, mas pode não resolver problemas grandes)
time_limit=120   # 2 minutos (bom compromisso)
time_limit=300   # 5 minutos (para problemas difíceis)
time_limit=600   # 10 minutos (análise profunda)
```

### Variar Pesos

```python
# Priorizar custo operacional
lambda1=0.8, lambda2=0.2

# Priorizar equilíbrio de carga
lambda1=0.2, lambda2=0.8

# Balanceado
lambda1=0.5, lambda2=0.5
```

---

## 📊 OUTPUTS GERADOS

Após a execução, o script gera **4 ficheiros**:

### 1. `batch_results.csv`
Tabela com todos os resultados (pode abrir no Excel):

| filename | num_patients | bb_time | bb_objective | sa_time | sa_objective | ... |
|----------|-------------|---------|--------------|---------|--------------|-----|
| s0m0.dat | 117 | 0.01 | 5380.91 | 0.17 | 5819.41 | ... |
| s1m0.dat | 125 | 0.02 | 6234.56 | 0.18 | 6521.32 | ... |

### 2. `batch_comparison.png`
Gráfico com boxplots comparando:
- Distribuição dos tempos de execução
- Distribuição dos desvios do ótimo

### 3. `scalability.png`
Gráfico scatter mostrando:
- Como o tempo aumenta com o tamanho do problema
- Comparação entre métodos

### 4. `batch_report.txt`
Relatório textual com estatísticas agregadas:
- Tempo médio/mediano/desvio padrão por método
- Desvio médio do ótimo
- Número de instâncias resolvidas otimamente

---

## 📈 ANÁLISE DOS RESULTADOS

### Abrir o CSV no Python

```python
import pandas as pd

df = pd.read_csv('/outputs/batch_results.csv')

# Ver resumo
print(df.describe())

# Ver instâncias mais difíceis
print(df.nlargest(10, 'bb_time'))

# Comparar métodos
print(df[['bb_time', 'sa_time', 'hybrid_time']].mean())
```

### Análises Úteis

```python
# Quantas instâncias o híbrido resolveu otimamente?
optimal_count = (df['hybrid_deviation'].abs() < 0.01).sum()
print(f"Híbrido ótimo em {optimal_count}/{len(df)} instâncias")

# Qual método é mais rápido em média?
print(df[['bb_time', 'sa_time', 'hybrid_time']].mean())

# Eficiência do híbrido vs B&B
speedup = df['bb_time'] / df['hybrid_time']
print(f"Híbrido é {speedup.mean():.2f}× a velocidade de B&B")
```

---

## ⏱️ ESTIMATIVAS DE TEMPO

### Por Instância (117 pacientes, 4 enfermarias):

| Método | Tempo Médio | Notas |
|--------|-------------|-------|
| Branch & Bound | ~0.01s | Muito rápido para pequenos problemas |
| Simulated Annealing | ~0.17s | Consistente |
| Tabu Search | ~22s | LENTO! Evitar para muitas instâncias |
| Híbrido | ~0.19s | Ligeiramente mais lento que B&B |

### Para 1000 Ficheiros:

| Configuração | Tempo Estimado |
|-------------|----------------|
| `['bb', 'sa', 'hybrid']` | **3-6 horas** |
| `['bb', 'sa']` | **2-4 horas** |
| `['bb', 'sa', 'tabu', 'hybrid']` | **10-20 horas** ⚠️ |

**Dica**: Começa com 10-50 ficheiros para estimar o tempo real!

---

## 💡 ESTRATÉGIAS RECOMENDADAS

### Estratégia 1: Amostragem (RÁPIDO)

```python
# Processar 50 ficheiros aleatórios
import random
analyzer.run_batch_analysis(
    pattern='*.dat',
    max_files=50,
    methods=['bb', 'sa', 'hybrid'],
    time_limit=120
)
```

**Vantagens**:
- Rápido (~30-45 minutos)
- Dá boa ideia dos resultados gerais
- Suficiente para relatório

### Estratégia 2: Por Grupo de M (ORGANIZADO)

```python
# Processar cada grupo separadamente
for m in [0, 1, 2, 3]:
    print(f"\n{'='*60}")
    print(f"Processando instâncias com M={m}")
    print(f"{'='*60}")
    
    analyzer = BatchAnalyzer('/uploads', 
                            f'/outputs/M{m}')
    
    analyzer.run_batch_analysis(
        pattern=f'*m{m}.dat',
        max_files=None,  # Todos deste grupo
        methods=['bb', 'sa', 'hybrid'],
        time_limit=120
    )
```

**Vantagens**:
- Organizado por categoria
- Pode correr cada grupo separadamente
- Fácil de analisar padrões

### Estratégia 3: Progressiva (SEGURA)

```python
# Começar com poucos, aumentar gradualmente
for batch_size in [10, 25, 50, 100]:
    print(f"\nProcessando {batch_size} ficheiros...")
    
    analyzer.run_batch_analysis(
        pattern='*.dat',
        max_files=batch_size,
        methods=['bb', 'sa', 'hybrid'],
        time_limit=120
    )
    
    # Verificar resultados antes de continuar
    input("Pressiona Enter para continuar...")
```

**Vantagens**:
- Seguro (pode parar a qualquer momento)
- Permite ajustar parâmetros entre batches
- Controlo total

---

## 🐛 RESOLUÇÃO DE PROBLEMAS

### Problema: "Demasiado lento!"

**Solução 1**: Reduzir métodos
```python
methods=['bb', 'hybrid']  # Excluir SA e Tabu
```

**Solução 2**: Reduzir time_limit
```python
time_limit=60  # Apenas 1 minuto
```

**Solução 3**: Processar menos ficheiros
```python
max_files=50  # Amostra
```

### Problema: "Gurobi timeout em muitas instâncias"

**Solução**: Aumentar time_limit
```python
time_limit=600  # 10 minutos
```

### Problema: "Script crashou a meio"

**Solução**: Os resultados são salvos progressivamente
- Verifica `batch_results.csv` - tem resultados parciais
- Podes retomar processando apenas ficheiros restantes

### Problema: "Memória insuficiente"

**Solução**: Processar em batches menores
```python
# Processar 100 de cada vez
for i in range(0, 1000, 100):
    analyzer.run_batch_analysis(
        max_files=100,
        # ...
    )
```

---

## 📊 EXEMPLO DE ANÁLISE COMPLETA

```python
from batch_analysis import BatchAnalyzer

# Configuração
analyzer = BatchAnalyzer(
    data_directory='/uploads',
    output_directory='/outputs'
)

# Processar
analyzer.run_batch_analysis(
    pattern='*.dat',
    max_files=100,          # 100 instâncias para análise robusta
    methods=['bb', 'sa', 'hybrid'],  # Métodos principais
    lambda1=0.5,
    lambda2=0.5,
    time_limit=180          # 3 minutos
)

# Analisar resultados
import pandas as pd

df = pd.read_csv('/outputs/batch_results.csv')

print("="*60)
print("RESUMO DA ANÁLISE")
print("="*60)

print(f"\nInstâncias processadas: {len(df)}")

print("\n📊 Tempos médios:")
print(f"  B&B:     {df['bb_time'].mean():.2f}s")
print(f"  SA:      {df['sa_time'].mean():.2f}s")
print(f"  Híbrido: {df['hybrid_time'].mean():.2f}s")

print("\n🎯 Qualidade:")
print(f"  SA desvio médio:      {df['sa_deviation'].mean():.2f}%")
print(f"  Híbrido desvio médio: {df['hybrid_deviation'].mean():.2f}%")

print("\n⭐ Híbrido ótimo:")
optimal = (df['hybrid_deviation'].abs() < 0.01).sum()
print(f"  {optimal}/{len(df)} instâncias ({optimal/len(df)*100:.1f}%)")
```

---

## 🎯 RECOMENDAÇÃO FINAL

Para o trabalho académico, sugiro:

1. **Teste inicial**: 10-20 ficheiros (verificar que funciona)
2. **Análise principal**: 50-100 ficheiros (estatisticamente relevante)
3. **Opcional**: 1000 ficheiros completos (se tiveres tempo e poder computacional)

**50-100 instâncias é suficiente** para:
- ✅ Demonstrar eficácia dos métodos
- ✅ Ter estatísticas robustas
- ✅ Identificar padrões
- ✅ Completar em tempo razoável (~1-2 horas)

---

## 📞 SUPORTE

Se tiveres dúvidas:
1. Começa com `max_files=5` para testar
2. Verifica os outputs gerados
3. Ajusta parâmetros conforme necessário

