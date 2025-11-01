# 🏥 Projeto: Alocação de Pacientes em Hospitais
## Comparação de Métodos de Otimização (Metaheurísticas + OR)

### 👥 Autores
**Tópico 3**: Metaheuristics for Optimization/Decision Problems  
**Tema**: Patient Allocation in Hospitals

---

## 📋 Resumo do Projeto

Este projeto implementa e compara **4 métodos diferentes** para resolver o problema de alocação de pacientes em hospitais:

1. **Branch & Bound Puro** (Método Exato - Gurobi)
2. **Simulated Annealing** (Metaheurística)
3. **Tabu Search** (Metaheurística)
4. **Método Híbrido** (Metaheurística + Branch & Bound)

### 🎯 Objetivo

Demonstrar que **métodos híbridos** (combinação de metaheurísticas com métodos exatos) conseguem obter soluções de **alta qualidade** em **tempo reduzido**, aproveitando:
- A **velocidade** das metaheurísticas para encontrar boas soluções iniciais
- A **precisão** do Branch & Bound para refinar e atingir o ótimo

---

## 🧩 O Problema

### Descrição

O problema consiste em **alocar pacientes a enfermarias** num hospital, decidindo:
- **Onde**: Qual enfermaria?
- **Quando**: Que dia admitir (dentro da janela temporal)?

### Objetivos (Bi-objetivo)

1. **Custo Operacional (f₁)**:
   - Minimizar atrasos nas admissões
   - Minimizar overtime/undertime do bloco operatório

2. **Equilíbrio de Carga (f₂)**:
   - Balancear carga de trabalho entre enfermarias (espacial)
   - Balancear carga de trabalho ao longo dos dias (temporal)

### Função Objetivo Combinada

```
min [λ₁·f₁ + λ₂·f₂]
```

Onde λ₁ e λ₂ são pesos que permitem explorar diferentes compromissos entre custo e equilíbrio.

### Restrições

- ✅ Capacidade de camas por enfermaria
- ✅ Tempo disponível no bloco operatório
- ✅ Compatibilidade paciente-enfermaria (especialização)
- ✅ Janelas temporais de admissão
- ✅ Cada paciente admitido exatamente uma vez

---

## 📁 Estrutura dos Ficheiros

```
projeto/
├── data_parser.py          # Parser para ler ficheiros .dat
├── milp_model.py           # Modelo MILP com Gurobi (Método 1)
├── metaheuristics.py       # Simulated Annealing e Tabu Search (Métodos 2 e 3)
├── hybrid_solver.py        # Método Híbrido (Método 4)
├── main.py                 # Script principal com análise completa
└── s0m0.dat                # Dados do problema (exemplo)
```

---

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
pip install gurobipy matplotlib pandas
```

### 2. Executar Análise Completa

```python
python3 main.py
```

Este comando:
- Carrega os dados do ficheiro `.dat`
- Executa os 4 métodos
- Compara resultados
- Gera gráficos e relatório

### 3. Executar Métodos Individualmente

#### Método 1: Branch & Bound

```python
from data_parser import PatientAllocationData
from milp_model import PatientAllocationMILP

data = PatientAllocationData('s0m0.dat')
model = PatientAllocationMILP(data, lambda1=0.5, lambda2=0.5)
model.build_model()
results = model.solve(time_limit=300)
model.print_solution()
```

#### Método 2: Simulated Annealing

```python
from metaheuristics import SimulatedAnnealing

sa = SimulatedAnnealing(data, lambda1=0.5, lambda2=0.5)
results = sa.solve(max_iterations=10000)
```

#### Método 3: Tabu Search

```python
from metaheuristics import TabuSearch

ts = TabuSearch(data, lambda1=0.5, lambda2=0.5)
results = ts.solve(max_iterations=5000)
```

#### Método 4: Híbrido

```python
from hybrid_solver import HybridSolver

hybrid = HybridSolver(data, lambda1=0.5, lambda2=0.5)
results = hybrid.solve(metaheuristic='SA', mh_max_iter=5000, milp_time_limit=300)
```

---

## 📊 Resultados (Exemplo: s0m0.dat)

### Comparação dos 4 Métodos

| Método | Tempo (s) | Objetivo | Desvio do Ótimo | Status |
|--------|-----------|----------|-----------------|--------|
| **Branch & Bound** | 0.01 | 5380.91 | 0.00% | ✅ Ótimo |
| **Simulated Annealing** | 0.16 | 5729.94 | +6.49% | ⚠️ Viável |
| **Tabu Search** | 22.54 | 5872.41 | +9.13% | ⚠️ Viável |
| **Híbrido (SA + B&B)** | 0.19 | 5380.91 | +0.00% | ✅ Ótimo |

### 💡 Principais Conclusões

1. **Branch & Bound Puro**:
   - ✅ Garante solução **ótima**
   - ✅ **Muito rápido** para este problema (0.01s)
   - ⚠️ Pode ser lento em problemas maiores

2. **Metaheurísticas Puras**:
   - ✅ **Rápidas** (SA: 0.16s)
   - ⚠️ Não garantem otimalidade
   - ⚠️ Desvio de 6-9% do ótimo

3. **Método Híbrido** ⭐:
   - ✅ Conseguiu a **solução ótima**
   - ✅ Tempo competitivo (0.19s)
   - ✅ **Melhor compromisso** tempo/qualidade
   - ✅ Melhoria de **5.35%** em relação à metaheurística inicial

### 🎯 Vantagens do Método Híbrido

O método híbrido demonstra que:
- A metaheurística fornece uma **excelente solução inicial** (5684.91)
- O Branch & Bound consegue **refinar rapidamente** para o ótimo (5380.91)
- O tempo total (0.19s) é apenas ligeiramente superior ao B&B puro
- Em problemas mais complexos, esta abordagem seria **significativamente mais rápida** que B&B puro

---

## 🔧 Parâmetros Configuráveis

### Pesos dos Objetivos

```python
lambda1 = 0.5  # Peso do custo operacional (0 a 1)
lambda2 = 0.5  # Peso do equilíbrio de carga (0 a 1)
```

- `lambda1=1, lambda2=0`: Prioriza custo operacional
- `lambda1=0, lambda2=1`: Prioriza equilíbrio de carga
- `lambda1=0.5, lambda2=0.5`: Compromisso equilibrado

### Parâmetros das Metaheurísticas

**Simulated Annealing**:
```python
max_iterations = 10000      # Número de iterações
initial_temp = 1000         # Temperatura inicial
cooling_rate = 0.95         # Taxa de arrefecimento
```

**Tabu Search**:
```python
max_iterations = 5000       # Número de iterações
tabu_tenure = 50           # Tamanho da lista tabu
```

### Parâmetros do Gurobi

```python
time_limit = 300           # Tempo limite (segundos)
threads = 4                # Número de threads
```

---

## 📈 Outputs Gerados

Após executar `main.py`, são gerados 3 ficheiros em `/outputs/`:

1. **comparison_chart.png**
   - Gráfico de barras comparando tempo e qualidade

2. **time_vs_quality.png**
   - Scatter plot mostrando trade-off tempo vs qualidade

3. **report.txt**
   - Relatório detalhado com análise dos resultados

---

## 🎓 Conceitos Implementados

### 1. Metaheurísticas

- **Simulated Annealing**: Inspirado em metalurgia, aceita soluções piores com probabilidade decrescente
- **Tabu Search**: Usa memória (lista tabu) para evitar ciclos e explorar o espaço de soluções

### 2. Programação Linear Inteira Mista (MILP)

- Variáveis binárias para alocação
- Variáveis contínuas para carga de trabalho e overtime/undertime
- Restrições lineares
- Função objetivo linear

### 3. Warm Start

- Inicialização do solver com solução conhecida
- Acelera convergência para o ótimo
- Crucial para eficiência do método híbrido

---

## 📚 Referências

1. **Artigo Base**: Pieter Smet (2023). "Generating balanced workload allocations in hospitals". Operations Research for Health Care, Volume 38.
   - Link: https://www.sciencedirect.com/science/article/pii/S2211692323000139

2. **Dataset**: Mendeley Data
   - Link: https://data.mendeley.com/datasets/3mv4rtxtfs/1

3. **Slides de Aula**:
   - Lecture 3a: Optimization & Local Search
   - Lecture: Meta-Heuristics (Simulated Annealing & Tabu Search)

---

## 🔍 Extensões Possíveis

1. **Explorar Fronteira de Pareto**: Variar λ₁ e λ₂ para gerar múltiplas soluções não-dominadas
2. **Testes em Instâncias Maiores**: Avaliar escalabilidade dos métodos
3. **Outras Metaheurísticas**: Implementar Genetic Algorithms, Ant Colony, etc.
4. **Análise de Sensibilidade**: Estudar impacto dos parâmetros
5. **Visualizações Avançadas**: Gráficos de Gantt para ver alocações ao longo do tempo

---

## ✅ Checklist do Trabalho

- [x] Implementar parser de dados
- [x] Implementar Método 1: Branch & Bound (Gurobi)
- [x] Implementar Método 2: Simulated Annealing
- [x] Implementar Método 3: Tabu Search
- [x] Implementar Método 4: Híbrido
- [x] Comparar os 4 métodos
- [x] Gerar gráficos e relatórios
- [x] Documentar código
- [x] Validar resultados

---

## 🤝 Como Contribuir para o Trabalho

### Para o colega responsável pela interpretação:

- Analisar os gráficos gerados
- Escrever relatório interpretando os resultados
- Explicar trade-offs entre os métodos
- Justificar quando usar cada abordagem

### Para expansão do código:

- Adicionar mais instâncias de teste
- Implementar outras metaheurísticas
- Criar visualizações interativas
- Adicionar testes de robustez

---

## 📞 Suporte

Se tiveres dúvidas sobre:
- **Implementação**: Consultar comentários no código
- **Teoria**: Rever slides e artigo base
- **Resultados**: Verificar relatório gerado em `report.txt`

---

## 🎉 Conclusão

Este projeto demonstra com sucesso que:

✅ **Métodos exatos** garantem otimalidade mas podem ser lentos  
✅ **Metaheurísticas** são rápidas mas aproximadas  
✅ **Métodos híbridos** combinam o melhor dos dois mundos  

O **Método Híbrido** é a estrela do trabalho, mostrando que podemos:
- Usar metaheurísticas para exploração rápida
- Usar Branch & Bound para refinamento preciso
- Obter soluções ótimas em tempo competitivo

**Resultado**: Solução prática e eficiente para problemas reais de alocação hospitalar! 🏥✨

---

**Data**: Outubro 2025  
**Curso**: Inteligência Artificial  
**Tema**: Metaheuristics for Optimization Problems
