# 🚀 GUIA RÁPIDO DE INÍCIO

## ⚡ Como Executar (3 Passos Simples)

### 1️⃣ Instalar Dependências

```bash
pip install gurobipy matplotlib pandas
```

### 2️⃣ Executar Análise Completa

```bash
python main.py
```

**Isto irá**:
- ✅ Carregar os dados do ficheiro `s0m0.dat`
- ✅ Executar os 4 métodos (Branch & Bound, SA, Tabu, Híbrido)
- ✅ Comparar resultados
- ✅ Gerar 3 ficheiros:
  - `comparison_chart.png` - Gráficos comparativos
  - `time_vs_quality.png` - Trade-off tempo vs qualidade
  - `report.txt` - Relatório detalhado

### 3️⃣ Ver Resultados

Abre os ficheiros gerados para analisar os resultados!

---

## 📝 Testes Rápidos Individuais

### Testar Branch & Bound

```python
python3 milp_model.py
```

### Testar Metaheurísticas

```python
python3 metaheuristics.py
```

### Testar Método Híbrido

```python
python3 hybrid_solver.py
```

---

## 🎯 O Que Esperar

### Resultados Típicos (s0m0.dat - 117 pacientes)

| Método | Tempo | Objetivo | Qualidade |
|--------|-------|----------|-----------|
| B&B | ~0.01s | 5380.91 | ✅ Ótimo |
| SA | ~0.16s | 5729.94 | ⚠️ +6.5% |
| Tabu | ~22s | 5872.41 | ⚠️ +9.1% |
| Híbrido | ~0.19s | 5380.91 | ✅ Ótimo |

**Conclusão**: Método Híbrido = Ótimo em tempo competitivo! 🎉

---

## 🔧 Modificar Parâmetros

### Alterar Pesos (Custo vs Equilíbrio)

Edita `main.py`, linha ~243:

```python
run_complete_comparison(
    data_file='/uploads/s0m0.dat',
    lambda1=0.7,  # ← Mais peso no custo
    lambda2=0.3,  # ← Menos peso no equilíbrio
    time_limit=180
)
```

### Usar Outro Ficheiro de Dados

```python
run_complete_comparison(
    data_file='caminho/para/outro_ficheiro.dat',
    lambda1=0.5,
    lambda2=0.5,
    time_limit=300
)
```

---

## ❓ Resolução de Problemas

### Erro: "Gurobi license"
- ✅ O código usa a licença académica gratuita do Gurobi
- ⚠️ Se não funcionar, verifica se tens licença válida em https://www.gurobi.com/

### Demasiado Lento
- Reduz `time_limit` em `main.py`
- Reduz `max_iterations` nas metaheurísticas

### Quer ver mais detalhes durante execução
- Muda `verbose=False` para `verbose=True` em `main.py`

---

## 📚 Estrutura do Código

```
data_parser.py          → Lê ficheiros .dat
milp_model.py           → Método 1 (B&B com Gurobi)
metaheuristics.py       → Métodos 2 e 3 (SA e Tabu)
hybrid_solver.py        → Método 4 (Híbrido)
main.py                 → Script principal (COMEÇA AQUI!)
```

---

## 🎓 Para o Relatório

### Dados Importantes a Mencionar:

1. **Método Híbrido conseguiu o ótimo em 0.19s**
   - Metaheurística encontrou solução inicial em 0.18s
   - B&B refinou para o ótimo em 0.01s
   - Melhoria de 5.35% sobre a solução inicial

2. **Comparação**:
   - SA: Rápido (+6.5% erro)
   - Tabu: Lento (+9.1% erro)
   - Híbrido: Rápido E ótimo ✅

3. **Conclusão**:
   - Métodos híbridos = Melhor dos dois mundos
   - Útil especialmente em problemas maiores

---

## ✨ Próximos Passos

- [ ] Testar com outros ficheiros .dat do dataset
- [ ] Variar λ₁ e λ₂ para explorar trade-offs
- [ ] Analisar os gráficos gerados
- [ ] Escrever interpretação dos resultados
- [ ] Preparar apresentação

---

Dúvidas, consulta o `README.md` completo para mais detalhes.
