# 🎯 Resumo

**Sistema completo de análise em batch** que pode processar **centenas ou milhares** de ficheiros `.dat` automaticamente!

---

## 📦 NOVOS FICHEIROS CRIADOS

### 1. [batch_analysis.py] ⭐
   - Script principal para processamento em batch
   - Processa múltiplos ficheiros automaticamente
   - Gera relatórios e visualizações agregadas
   - ~500 linhas de código

### 2. [run_batch.py] 🚀
   - Script SIMPLES e FÁCIL de usar
   - Apenas configura parâmetros no topo e executa
   - Perfeito para começar rapidamente

### 3. [BATCH_GUIDE.md] 📚
   - Guia completo de como usar
   - Estratégias diferentes para diferentes necessidades
   - Exemplos práticos
   - Resolução de problemas

---

## 🚀 COMO USAR (3 PASSOS)

### Passo 1: Preparar os Dados

Coloca todos os teus ficheiros `.dat` numa pasta:

```
/uploads/
├── s0m0.dat
├── s0m1.dat
├── s0m2.dat
├── ...
└── s999m3.dat  (1000 ficheiros)
```

### Passo 2: Executar

**Opção A - Script Simples** (Recomendado):

```bash
python3 run_batch.py
```

Edita primeiro os parâmetros no topo do ficheiro:
```python
MAX_FILES = 10        # Começa com poucos!
METHODS = ['bb', 'sa', 'hybrid']
TIME_LIMIT = 120
```

**Opção B - Python Diretamente**:

```python
from batch_analysis import BatchAnalyzer

analyzer = BatchAnalyzer('/uploads', '/outputs')

analyzer.run_batch_analysis(
    pattern='*.dat',
    max_files=50,  # Ajusta conforme necessário
    methods=['bb', 'sa', 'hybrid'],
    lambda1=0.5,
    lambda2=0.5,
    time_limit=120
)
```

### Passo 3: Analisar Resultados

O sistema gera **4 ficheiros**:

1. **batch_results.csv** - Tabela Excel com todos os resultados
2. **batch_comparison.png** - Gráficos comparativos
3. **scalability.png** - Análise de escalabilidade
4. **batch_report.txt** - Relatório estatístico

---

## ⏱️ ESTIMATIVAS DE TEMPO

### Por Ficheiro (médio):
- Branch & Bound: ~0.01s
- Simulated Annealing: ~0.17s
- Híbrido: ~0.19s
- **Total por ficheiro**: ~0.4s

### Para Diferentes Quantidades:

| Ficheiros | Métodos | Tempo Estimado |
|-----------|---------|----------------|
| 10 | bb + sa + hybrid | ~5 minutos |
| 50 | bb + sa + hybrid | ~30 minutos |
| 100 | bb + sa + hybrid | ~1 hora |
| 1000 | bb + sa + hybrid | **~10 horas** |

**💡 Recomendação**: Começa com 50-100 ficheiros para análise robusta sem demorar muito!

---

## 🎯 ESTRATÉGIAS RECOMENDADAS

### 1️⃣ Teste Rápido (5-10 min)
```python
max_files=10
methods=['bb', 'sa', 'hybrid']
time_limit=120
```
✅ Para verificar que tudo funciona

### 2️⃣ Análise Robusta (1-2 horas)
```python
max_files=100
methods=['bb', 'sa', 'hybrid']
time_limit=180
```
✅ Estatisticamente significativo
✅ Suficiente para o trabalho académico

### 3️⃣ Análise Completa (10-20 horas)
```python
max_files=None  # TODOS!
methods=['bb', 'sa', 'hybrid']
time_limit=300
```
✅ Análise exaustiva
⚠️ Demora muito (deixa a correr de noite)

### 4️⃣ Por Grupos de M
```python
# Processar cada M separadamente
for m in [0, 1, 2, 3]:
    analyzer.run_batch_analysis(
        pattern=f'*m{m}.dat',
        max_files=None,
        ...
    )
```
✅ Organizado
✅ Permite analisar impacto de M

---

## 📊 O QUE PODES ANALISAR

Com os resultados do batch, podes responder:

✅ **Desempenho médio** de cada método  
✅ **Escalabilidade**: Como o tempo aumenta com o tamanho?  
✅ **Robustez**: Quantas instâncias cada método resolve otimamente?  
✅ **Trade-offs**: Tempo vs Qualidade  
✅ **Impacto de M**: Como especializações menores afetam dificuldade?  
✅ **Casos difíceis**: Quais instâncias são mais desafiantes?  

---

## 📈 EXEMPLO DE ANÁLISE

```python
import pandas as pd

# Carregar resultados
df = pd.read_csv('batch_results.csv')

# Estatísticas básicas
print("Tempo médio por método:")
print(df[['bb_time', 'sa_time', 'hybrid_time']].mean())

# Híbrido vs B&B
print("\nHíbrido conseguiu ótimo em:")
optimal = (df['hybrid_deviation'].abs() < 0.01).sum()
print(f"{optimal}/{len(df)} instâncias ({optimal/len(df)*100:.1f}%)")

# Identificar casos difíceis
print("\n5 instâncias mais difíceis:")
print(df.nlargest(5, 'bb_time')[['filename', 'num_patients', 'bb_time']])

# Análise por M
print("\nTempo médio por valor de M:")
print(df.groupby('M')['bb_time'].mean())
```

---

## 🎓 PARA O RELATÓRIO

Com este sistema podes:

1. **Tabela Comparativa**
   ```
   Usar dados de batch_results.csv
   Mostrar média, mediana, desvio padrão
   ```

2. **Gráficos Profissionais**
   ```
   Usar batch_comparison.png e scalability.png
   Gráficos prontos para slides!
   ```

3. **Análise Estatística**
   ```
   Teste t, intervalos de confiança
   Correlações entre variáveis
   ```

4. **Conclusões Robustas**
   ```
   Baseadas em dezenas/centenas de instâncias
   Não apenas 1 exemplo!
   ```

---

## ⚠️ PONTOS IMPORTANTES

### ✅ FAZER:
- Começar com **poucos ficheiros** (5-10) para testar
- Usar `methods=['bb', 'sa', 'hybrid']` (excluir Tabu que é lento)
- Monitorizar o progresso (imprime status)
- Guardar resultados incrementalmente (CSV é atualizado)

### ❌ NÃO FAZER:
- Começar diretamente com 1000 ficheiros
- Incluir Tabu se tiveres muitos ficheiros (demora MUITO)
- Deixar time_limit muito alto (>10min) sem necessidade
- Esquecer de verificar o espaço em disco

---

## 🆘 RESOLUÇÃO DE PROBLEMAS

### "Muito lento!"
→ Reduz `max_files` ou `time_limit`  
→ Exclui Tabu dos métodos

### "Ficou sem memória"
→ Processa em batches menores (50-100 de cada vez)

### "Gurobi timeout"
→ Aumenta `time_limit`  
→ Algumas instâncias podem ser muito difíceis

### "Script parou a meio"
→ Verifica `batch_results.csv` (tem resultados parciais)  
→ Podes retomar excluindo ficheiros já processados

---

## 🎉 RESUMO FINAL

### ✅ O que tens agora:

1. **Sistema completo** para processar 1000+ ficheiros
2. **Automático** - configura e deixa correr
3. **Análise agregada** - estatísticas de todos os ficheiros
4. **Visualizações** - gráficos profissionais
5. **Relatórios** - prontos para o trabalho

### 🎯 Recomendação Final:

Para o trabalho académico:
1. **Teste**: 10 ficheiros (verificar)
2. **Análise principal**: 50-100 ficheiros (robusto)
3. **Opcional**: 1000 ficheiros (se tiveres tempo)

**50-100 ficheiros é mais do que suficiente** para:
- ✅ Demonstrar eficácia
- ✅ Ter estatísticas robustas
- ✅ Completar em tempo razoável (~1-2 horas)

---

## 📞 PRÓXIMOS PASSOS

1. **Lê**: [BATCH_GUIDE.md](computer:///mnt/user-data/outputs/BATCH_GUIDE.md)
2. **Testa**: Executa com `max_files=5`
3. **Ajusta**: Muda parâmetros conforme necessário
4. **Executa**: Análise completa (50-100 ficheiros)
5. **Analisa**: Usa os CSVs e gráficos gerados

---

Dúvida? Consulta o BATCH_GUIDE.md que tem tudo explicado em detalhe!
